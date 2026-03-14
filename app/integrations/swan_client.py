from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import httpx

from app.integrations.swan_exceptions import SwanAPIError, SwanAuthError, SwanError

logger = logging.getLogger(__name__)

TRANSACTIONS_QUERY = """
query GetTransactions($after: DateTime, $before: DateTime) {
  me {
    accounts(first: 1) {
      edges {
        node {
          transactions(after: $after, before: $before, first: 100) {
            edges {
              node {
                id
                amount {
                  value
                  currency
                  displayedDecimals
                }
                label
                reference
                bookingDate
                valueDate
                direction
                status
                counterparty {
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

ACCOUNT_BALANCE_QUERY = """
query GetAccountBalance {
  me {
    accounts(first: 1) {
      edges {
        node {
          id
          name
          balance {
            value
            currency
          }
        }
      }
    }
  }
}
"""


class SwanClient:
    """Client for Swan GraphQL API."""

    def __init__(self, api_url: str, access_token: str) -> None:
        """Initialize Swan client.

        Args:
            api_url: Swan API GraphQL endpoint URL.
            access_token: Bearer token for authentication.

        Raises:
            ValueError: If api_url or access_token is empty.
        """
        if not api_url or not access_token:
            raise ValueError("api_url and access_token are required")

        self._api_url = api_url
        self._access_token = access_token
        self._max_retries = 2
        self._retry_delay = 1  # seconds

    async def get_transactions(
        self,
        from_date: date,
        to_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch bank transactions from Swan.

        Args:
            from_date: Start date for transactions.
            to_date: End date for transactions (defaults to today).

        Returns:
            List of transaction dictionaries.

        Raises:
            SwanAuthError: If authentication fails.
            SwanAPIError: If API call fails.
        """
        if to_date is None:
            from datetime import datetime

            to_date = datetime.now().date()

        if from_date > to_date:
            raise ValueError(f"from_date ({from_date}) must be <= to_date ({to_date})")

        # Convert dates to ISO format with time
        after_str = f"{from_date}T00:00:00Z"
        before_str = f"{to_date}T23:59:59Z"

        variables = {
            "after": after_str,
            "before": before_str,
        }

        try:
            response = await self._execute_query(TRANSACTIONS_QUERY, variables)
            transactions = self._parse_transactions(response)
            logger.info(
                "Transactions fetched from Swan",
                extra={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                    "count": len(transactions),
                },
            )
            return transactions
        except SwanError:
            raise
        except Exception as e:
            logger.error(
                "Failed to fetch transactions from Swan",
                exc_info=True,
                extra={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                },
            )
            raise SwanAPIError(f"Failed to fetch transactions: {str(e)}") from e

    async def get_account_balance(self) -> dict[str, Any]:
        """Get current account balance.

        Returns:
            Dictionary with account id, name, balance value, and currency.

        Raises:
            SwanAuthError: If authentication fails.
            SwanAPIError: If API call fails.
        """
        try:
            response = await self._execute_query(ACCOUNT_BALANCE_QUERY, {})
            balance = self._parse_account_balance(response)
            logger.info("Account balance fetched from Swan", extra=balance)
            return balance
        except SwanError:
            raise
        except Exception as e:
            logger.error("Failed to fetch account balance from Swan", exc_info=True)
            raise SwanAPIError(f"Failed to fetch account balance: {str(e)}") from e

    async def _execute_query(
        self,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute GraphQL query with retry logic.

        Args:
            query: GraphQL query string.
            variables: Query variables.

        Returns:
            GraphQL response data.

        Raises:
            SwanAuthError: If authentication fails.
            SwanAPIError: If API call fails after retries.
        """
        payload = {
            "query": query,
            "variables": variables,
        }

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self._api_url,
                        json=payload,
                        headers=headers,
                    )

                    if response.status_code in (401, 403):
                        raise SwanAuthError(f"Authentication failed: {response.status_code}")

                    if response.status_code >= 500:
                        if attempt < self._max_retries:
                            await asyncio.sleep(self._retry_delay * (2**attempt))
                            continue
                        raise SwanAPIError(f"Server error: {response.status_code} {response.text}")

                    if response.status_code >= 400:
                        raise SwanAPIError(f"Client error: {response.status_code} {response.text}")

                    data = response.json()

                    # Check for GraphQL errors
                    if "errors" in data:
                        errors = data.get("errors", [])
                        error_message = "; ".join(
                            [e.get("message", "Unknown error") for e in errors]
                        )
                        raise SwanAPIError(f"GraphQL error: {error_message}")

                    return data.get("data", {})

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay * (2**attempt))
                    continue
                raise SwanAPIError(f"Network error: {str(e)}") from e

        raise SwanAPIError("Max retries exceeded")

    def _parse_transactions(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse transactions from GraphQL response.

        Args:
            response: GraphQL response data.

        Returns:
            List of parsed transaction dictionaries.

        Raises:
            SwanAPIError: If response structure is invalid.
        """
        try:
            accounts = response.get("me", {}).get("accounts", {}).get("edges", [])
            if not accounts:
                return []

            account = accounts[0].get("node", {})
            transactions_data = account.get("transactions", {}).get("edges", [])

            transactions = []
            for edge in transactions_data:
                node = edge.get("node", {})
                amount_data = node.get("amount", {})

                transaction = {
                    "id": node.get("id"),
                    "amount": amount_data.get("value"),
                    "currency": amount_data.get("currency", "EUR"),
                    "label": node.get("label", ""),
                    "reference": node.get("reference"),
                    "booking_date": node.get("bookingDate"),
                    "value_date": node.get("valueDate"),
                    "type": "CREDIT" if node.get("direction") == "In" else "DEBIT",
                    "status": node.get("status"),
                    "counterparty": node.get("counterparty", {}).get("name"),
                }

                if transaction.get("id") and transaction.get("amount"):
                    transactions.append(transaction)

            return transactions

        except (KeyError, TypeError, AttributeError) as e:
            raise SwanAPIError(f"Invalid response structure: {str(e)}") from e

    def _parse_account_balance(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse account balance from GraphQL response.

        Args:
            response: GraphQL response data.

        Returns:
            Parsed account balance dictionary.

        Raises:
            SwanAPIError: If response structure is invalid.
        """
        try:
            accounts = response.get("me", {}).get("accounts", {}).get("edges", [])
            if not accounts:
                raise SwanAPIError("No accounts found in response")

            account = accounts[0].get("node", {})
            balance_data = account.get("balance", {})

            return {
                "account_id": account.get("id"),
                "account_name": account.get("name"),
                "balance_value": balance_data.get("value"),
                "currency": balance_data.get("currency", "EUR"),
            }

        except (KeyError, TypeError, AttributeError) as e:
            raise SwanAPIError(f"Invalid response structure: {str(e)}") from e
