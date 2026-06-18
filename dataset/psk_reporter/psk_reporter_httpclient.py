import time as _time
import requests
import pandas as pd
import pickle
import gzip

from io import StringIO
import dataset.psk_reporter.listenerstationclusters as lsc
from extra.feedback import feedback_handler

class PSKReporter():
    url = "https://retrieve.pskreporter.info/query"

    # Retry policy for transient server-side failures (e.g. Cloudflare 502/503).
    MAX_RETRIES = 5
    BACKOFF_BASE_S = 5

    def __init__(self, callsign):
        self.senderCallsign = callsign

    def _fetch_xml(self, params):
        """Query PSK Reporter and return the XML body as a string.

        Retries transient failures (network errors and 5xx responses, which
        PSK Reporter serves as a Cloudflare HTML error page rather than XML)
        with exponential backoff. Returns None if no XML could be obtained.
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                r = requests.get(self.url, params=params, timeout=30)
            except requests.RequestException as e:
                print(f"PSK Reporter request failed (attempt {attempt}/{self.MAX_RETRIES}): {e}")
            else:
                ctype = r.headers.get("Content-Type", "")
                body = r.text.lstrip()
                is_html = body[:5].lower() == "<!doc" or body[:5].lower() == "<html" \
                    or "html" in ctype.lower()

                if r.status_code == 200 and not is_html:
                    return r.text
                # 5xx / HTML error page => transient; anything else, log and retry too.
                print(f"PSK Reporter returned a non-XML response "
                      f"(status {r.status_code}, content-type '{ctype}') "
                      f"on attempt {attempt}/{self.MAX_RETRIES}.")

            if attempt < self.MAX_RETRIES:
                delay = self.BACKOFF_BASE_S * (2 ** (attempt - 1))
                print(f"Retrying in {delay}s...")
                _time.sleep(delay)

        print("PSK Reporter unreachable after retries; skipping this query.")
        feedback_handler(
            f"PSK Reporter fetch FAILED for {self.senderCallsign} after "
            f"{self.MAX_RETRIES} attempts (server unreachable / non-XML response). "
            f"Skipping this query."
        )
        return None

    def get_report(self, appcontact, time=30):

        params = {
            "senderCallsign" : self.senderCallsign,
            "flowStartSeconds": time * (-60),
            "appcontact": appcontact
        }

        # Sending a request to PSK Reporter.
        try:
            xml_text = self._fetch_xml(params)
            if xml_text is None:
                return -1

            report = {}

            # If the XML is HTML-escaped (e.g., &lt; and &gt;), decode it first
            xml_string = xml_text.replace("&lt;", "<").replace("&gt;", ">")

            # Reports that contains the given callsign.
            try:
                df_reception_report = pd.read_xml(StringIO(xml_string), xpath=".//receptionReport")

            except ValueError as ve:
                print("No reception reports...")
                df_reception_report = pd.DataFrame()

            except Exception as e:
                # Reaching here means a 200 response that still wasn't parseable
                # XML. Save it for inspection but keep the experiment running.
                print(f"Caught error {e}!")
                with open('error_xml.html', 'w') as f:
                    f.write(xml_text)
                feedback_handler(
                    f"PSK Reporter returned a 200 response for {self.senderCallsign} "
                    f"that could not be parsed as XML ({e}). Saved to error_xml.html, "
                    f"skipping this query."
                )
                return -1

            report['reception_reports'] = df_reception_report

            # Callsigns that were recently reported as active.
            df_active_cs = pd.read_xml(StringIO(xml_string), xpath=".//activeCallsign")
            report['active_cs'] = df_active_cs

            # This are the stations that are currently active.
            df_active_receivers = pd.read_xml(StringIO(xml_string), xpath=".//activeReceiver")
            clusters = lsc.ListenerStationClusters(df_active_receivers, 11)
            report['active_receivers'] = clusters.clusters_params
            report['maidenhead_matrix'] = clusters.distribution_matrix

            df_active_receivers = pd.read_xml(StringIO(xml_string), xpath=".//activeReceiver")
            df_active_receivers_reduced = df_active_receivers[['callsign', 'locator', 'frequency', 'mode']]
            df_active_receivers_reduced = df_active_receivers_reduced[df_active_receivers_reduced['mode'] == "FT8"]
            report['active_receivers'] = df_active_receivers_reduced

            # Contains the senderCallsign and the most recent unix epoch of when a transmission from senderCallsign was reported.
            #df_sender_search = pd.read_xml(StringIO(xml_string), xpath=".//senderSearch")

            # Unique identifier for the PSK Reporter request, not really useful for the dataset.
            #df_last_sequence_number = pd.read_xml(StringIO(xml_string), xpath=".//lastSequenceNumber")

            # Unix epoch of the last report contained in this response.
            df_max_flow_start_seconds = pd.read_xml(StringIO(xml_string), xpath=".//maxFlowStartSeconds")
            report['last_report_time'] = df_max_flow_start_seconds['value'][0]

            print(report)

        except ValueError as ve:
            print(f"Unable to query data for this sample! {ve}")
            report = -1

        return report

