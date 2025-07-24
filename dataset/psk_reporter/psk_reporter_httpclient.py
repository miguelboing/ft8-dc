import requests
import pandas as pd
from io import StringIO
import dataset.psk_reporter.listenerstationclusters as lsc

class PSKReporter():
    url = "https://retrieve.pskreporter.info/query"

    def __init__(self, callsign):
        self.senderCallsign = callsign

    def get_report(self, time=30):
        params = {
            "senderCallsign" : self.senderCallsign,
            "time": time
        }

        # Sending a request to PSK Reporter.
        try:
            r = requests.get(self.url, params=params)

            report = {}

            # If the XML is HTML-escaped (e.g., &lt; and &gt;), decode it first
            xml_string = r.text.replace("&lt;", "<").replace("&gt;", ">")

            # Reports that contains the given callsign.
            try:
                df_reception_report = pd.read_xml(StringIO(xml_string), xpath=".//receptionReport")
            except ValueError as ve:
                print("No reception reports...")
                df_reception_report = pd.DataFrame()

            report['reception_reports'] = df_reception_report

            # Callsigns that were recently reported as active.
            df_active_cs = pd.read_xml(StringIO(xml_string), xpath=".//activeCallsign")
            report['active_cs'] = df_active_cs

            # This are the stations that are currently active.
            df_active_receivers = pd.read_xml(StringIO(xml_string), xpath=".//activeReceiver")
            clusters = lsc.ListenerStationClusters(df_active_receivers, 11)
            report['active_receivers'] = clusters.clusters_params
            report['maidenhead_matrix'] = clusters.distribution_matrix

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

