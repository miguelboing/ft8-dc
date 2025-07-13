import pandas as pd

from dataset.psk_reporter.psk_reporter_httpclient import PSKReporter

class Dataset(PSKReporter):
    def __init__(self, callsign, columns):
        self.df = pd.DataFrame(columns=columns, dtype="object")
        PSKReporter().__init__(callsign)

    # Export data into a dictionary
    def to_dict(self):
        return self.df.to_dict(orient='records')

    # Add new samples
    def add_row(self, row):
        row = row[self.columns]
        if (self.df.empty):
            self.df = row.copy()
        else:
            self.df = pd.concat([self.df, row], ignore_index = True, copy=False)

    #Use this method to import the csv to a dataframe
    @classmethod
    def from_csv(cls, name, columns):
        data = pd.read_csv(name)
        return cls(data.to_dict(orient='records'), columns)

    def save_csv(self, name = ""):
        self.df.to_csv(name, index=False)

    @property(self):
    def df(self):
        return self.df

class DecodeDataset(Dataset):
    decode_columns = ["wsjtx_id", "new_decode", "millis_since_midnight", "time",
                    "snr", "delta_t", "delta_f", "mode", "message", "low_confidence",
                    "off_air"]

    status_columns = ["s_id", "s_dial_frequency", "s_mode", "s_dx_call", "s_report",
                      "s_tx_mode", "s_tx_enabled", "s_transmitting", "s_decoding",
                      "s_rx_df", "s_tx_df", "s_de_call", "s_de_grid", "s_dx_grid",
                      "s_tx_watchdog", "s_sub_mode", "s_fast_mode", "s_special_op_mode",
                      "s_frequency_tolerance", "s_tr_period", "s_config_name",
                      "s_tx_message"]

    columns = decode_columns + status_columns

    def __init__(self, callsign):
        self.status_dict = {}
        Dataset.__init__(self, callsign, self.columns)

    def set_status_info(self, status_dict):
        self.status_dict = status_dict

    def add_new_sample(self, sample_dict):
        sample_dict.update(self.status_dict)

        df_temp = pd.DataFrame([sample_dict], columns=self.columns)

        self.add_row(df_temp)

