import pandas as pd

class Dataset:
    def __init__(self, filename, columns):
        self.df = pd.DataFrame(columns=columns)
        self.filename = filename

    # Export data into a dictionary
    def to_dict(self):
        return self.df.to_dict(orient='records')

    # Add new samples
    def add_row(self, row):
        self.df = pd.concat([self.df, row], ignore_index = True)

    #Use this method to import the csv to a dataframe
    @classmethod
    def from_csv(cls, columns):
        data = pd.read_csv(self.filename)
        return cls(data.to_dict(orient='records'), columns)

    def save_csv(self):
        self.df.to_csv(self.filename, index=False)

class DecodeDataset(Dataset):
    def __init__(self):
        Dataset.__init__(self, './dataset/output/' + 'decodedataset.csv', ["wsjtx_id", "new_decode", "millis_since_midnight", "time",
                                "snr", "delta_t", "delta_f", "mode", "message", "low_confidence",
                                "off_air"])

    def add_new_sample(self, sample_dict):
        df_temp = pd.DataFrame.from_dict({'name':sample_dict.keys(), 'value':sample_dict.values()})

        self.add_row(df_temp)
        self.df.to_csv(self.filename, index=False)
        import sys
        sys.exit(0)
