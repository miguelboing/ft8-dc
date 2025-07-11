import requests
import pandas as pd
from io import StringIO
import listernerstationsclusters as lsc

class PSK_Reporter:
    url = "https://retrieve.pskreporter.info/query"
    def __init__(self, callsign):
        self.senderCallsign = callsign,

    def get_report(self, time=30, name=""):
        params = {
            "senderCallsign" : self.senderCallsign,
            "time": time
        }

        # Sending a request to PSK Reporter
        r = requests.get(url, params=params)

        # If the XML is HTML-escaped (e.g., &lt; and &gt;), decode it first
        xml_string = r.text.replace("&lt;", "<").replace("&gt;", ">")

        # Reports that contains the given callsign.
        df_reception_report = pd.read_xml(StringIO(xml_string), xpath=".//receptionReport")

        # Callsigns that were recently reported as active.
        df_active_cs = pd.read_xml(StringIO(xml_string), xpath=".//activeCallsign")

        # This are the stations that are currently active.
        df_active_receiver = pd.read_xml(StringIO(xml_string), xpath=".//activeReceiver")
        clusters = lsc.ListenerStationClusters(df_active_receiver)
        clusters.save_to_pklgz(name)

        # Contains the senderCallsign and the most recent unix epoch of when a transmission from senderCallsign was reported.
        df_sender_search = pd.read_xml(StringIO(xml_string), xpath=".//senderSearch")

        # Unique identifier for the PSK Reporter request, not really useful for the dataset.
        df_last_sequence_number = pd.read_xml(StringIO(xml_string), xpath=".//lastSequenceNumber")

        # Unix epoch of the last report contained in this response.
        df_max_flow_start_seconds = pd.read_xml(StringIO(xml_string), xpath=".//maxFlowStartSeconds")


