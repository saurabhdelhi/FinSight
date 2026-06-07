"""
Tally Prime XML HTTP API Connector.

Communicates with Tally Prime via POST requests to its XML HTTP API
(default port 9000).  Each method builds an XML envelope, sends it,
and returns the raw XML response for the parser to handle.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.exceptions import TallyConnectionError, TallyDataError

logger = logging.getLogger(__name__)

# ── XML Request Templates ────────────────────────────────────────────────

_ENVELOPE = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>{request_type}</TALLYREQUEST>
    <TYPE>{data_type}</TYPE>
    <ID>{data_id}</ID>
  </HEADER>
  <BODY>
    <DESC>
      {desc_body}
    </DESC>
  </BODY>
</ENVELOPE>"""

_STATIC_VARS_XML_EXPORT = """<STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>"""

_STATIC_VARS_EXPLODE = """<STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <EXPLODEFLAG>Yes</EXPLODEFLAG>
      </STATICVARIABLES>"""

_LEDGER_COLLECTION_TDL = """<TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="FinSightLedgers" ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No">
            <TYPE>Ledger</TYPE>
            <FETCHLIST>
              <FETCH>NAME</FETCH>
              <FETCH>PARENT</FETCH>
              <FETCH>OPENINGBALANCE</FETCH>
              <FETCH>CLOSINGBALANCE</FETCH>
              <FETCH>GUID</FETCH>
              <FETCH>ALTERID</FETCH>
              <FETCH>ADDRESS.LIST</FETCH>
              <FETCH>LEDSTATENAME</FETCH>
              <FETCH>GSTREGISTRATIONTYPE</FETCH>
              <FETCH>PARTYGSTIN</FETCH>
              <FETCH>INCOMETAXNUMBER</FETCH>
              <FETCH>ISBILLWISEON</FETCH>
              <FETCH>ISCOSTCENTRESON</FETCH>
            </FETCHLIST>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>"""

_GROUP_COLLECTION_TDL = """<TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="FinSightGroups" ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No">
            <TYPE>Group</TYPE>
            <FETCHLIST>
              <FETCH>NAME</FETCH>
              <FETCH>PARENT</FETCH>
              <FETCH>GUID</FETCH>
              <FETCH>ALTERID</FETCH>
              <FETCH>ISREVENUE</FETCH>
              <FETCH>ISDEEMEDPOSITIVE</FETCH>
              <FETCH>AFFECTSGROSSPROFIT</FETCH>
              <FETCH>SORTPOSITION</FETCH>
            </FETCHLIST>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>"""

_VOUCHER_COLLECTION_TDL = """<TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="FinSightVouchers" ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No">
            <TYPE>Voucher</TYPE>
            <FETCHLIST>
              <FETCH>DATE</FETCH>
              <FETCH>GUID</FETCH>
              <FETCH>ALTERID</FETCH>
              <FETCH>VOUCHERTYPENAME</FETCH>
              <FETCH>VOUCHERNUMBER</FETCH>
              <FETCH>PARTYLEDGERNAME</FETCH>
              <FETCH>AMOUNT</FETCH>
              <FETCH>NARRATION</FETCH>
              <FETCH>ISCANCELLED</FETCH>
              <FETCH>ISOPTIONAL</FETCH>
              <FETCH>ALLLEDGERENTRIES.LIST</FETCH>
            </FETCHLIST>
            <FILTER>FinsightDateFilter</FILTER>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="FinsightDateFilter">
              $Date &gt;= $FinsightFromDate AND $Date &lt;= $FinsightToDate
          </SYSTEM>
        </TDLMESSAGE>
      </TDL>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <FinsightFromDate>{from_date}</FinsightFromDate>
        <FinsightToDate>{to_date}</FinsightToDate>
      </STATICVARIABLES>"""


class TallyConnector:
    """
    Async client for the Tally Prime XML HTTP API.

    Usage:
        connector = TallyConnector(host="192.168.1.5", port=9000)
        xml = await connector.fetch_ledgers()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9000,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    async def _post(self, xml_payload: str) -> str:
        """Send an XML POST to Tally and return the response body."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    content=xml_payload.encode("utf-8"),
                    headers={"Content-Type": "text/xml; charset=utf-8"},
                )
                response.raise_for_status()
                return response.text
        except httpx.ConnectError as exc:
            raise TallyConnectionError(
                self.host, self.port,
                "Connection refused. Is Tally Prime running with server mode enabled?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TallyConnectionError(
                self.host, self.port,
                f"Request timed out after {self.timeout}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise TallyConnectionError(
                self.host, self.port,
                f"HTTP {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            raise TallyConnectionError(
                self.host, self.port, str(exc)
            ) from exc

    # ── Public Methods ───────────────────────────────────────────────────

    async def test_connection(self) -> str:
        """
        Ping Tally by requesting active company info.
        Returns the company name on success.
        """
        xml = _ENVELOPE.format(
            request_type="Export",
            data_type="Data",
            data_id="List of Companies",
            desc_body=_STATIC_VARS_XML_EXPORT,
        )
        response_xml = await self._post(xml)
        # Quick sanity check — if we get a parseable XML back, Tally is alive
        if "<ENVELOPE>" not in response_xml:
            raise TallyDataError("Unexpected response from Tally")
        return response_xml

    async def fetch_company_info(self) -> str:
        """Fetch information about the currently active company in Tally."""
        xml = _ENVELOPE.format(
            request_type="Export",
            data_type="Data",
            data_id="List of Companies",
            desc_body=_STATIC_VARS_XML_EXPORT,
        )
        return await self._post(xml)

    async def fetch_groups(self) -> str:
        """Fetch all account groups with their hierarchy."""
        xml = _ENVELOPE.format(
            request_type="Export",
            data_type="Collection",
            data_id="FinSightGroups",
            desc_body=_GROUP_COLLECTION_TDL,
        )
        return await self._post(xml)

    async def fetch_ledgers(self) -> str:
        """
        Fetch all ledgers with opening/closing balance, parent group,
        GUID, AlterID, and party details.
        """
        xml = _ENVELOPE.format(
            request_type="Export",
            data_type="Collection",
            data_id="FinSightLedgers",
            desc_body=_LEDGER_COLLECTION_TDL,
        )
        return await self._post(xml)

    async def fetch_vouchers(self, from_date: str, to_date: str) -> str:
        """
        Fetch all vouchers within a date range.

        Args:
            from_date: Start date in Tally format (YYYYMMDD) e.g. "20250401"
            to_date:   End date in Tally format (YYYYMMDD) e.g. "20260331"
        """
        desc_body = _VOUCHER_COLLECTION_TDL.format(
            from_date=from_date, to_date=to_date
        )
        xml = _ENVELOPE.format(
            request_type="Export",
            data_type="Collection",
            data_id="FinSightVouchers",
            desc_body=desc_body,
        )
        return await self._post(xml)

    async def fetch_trial_balance(self) -> str:
        """Fetch the trial balance report with all ledgers exploded."""
        xml = _ENVELOPE.format(
            request_type="Export",
            data_type="Data",
            data_id="Trial Balance",
            desc_body=_STATIC_VARS_EXPLODE,
        )
        return await self._post(xml)
