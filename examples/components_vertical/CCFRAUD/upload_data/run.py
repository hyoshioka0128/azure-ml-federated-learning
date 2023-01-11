"""Script for mock components."""
import argparse
import logging
import sys
import os

import pandas as pd

from sklearn.preprocessing import OneHotEncoder
from zipfile import ZipFile
from azureml.core import Run, Workspace
from azureml.core.keyvault import Keyvault

CATEGORICAL_PROPS = ["category", "region", "gender", "state", "job"]
ENCODERS = {}


def get_kaggle_client(kv: Keyvault):
    """Gets the Kaggle client

    Args:
        kv (Keyvault): keyvault to use for retrieving Kaggle credentials
    """

    os.environ["KAGGLE_USERNAME"] = kv.get_secret("kaggleusername")
    os.environ["KAGGLE_KEY"] = kv.get_secret("kagglekey")

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    return api


def fit_encoders(df):
    """Creates one-hot encodings for categorical data

    Args:
        df (pd.DataFrame): Pandas dataframe to use to provide us with all unique value for each categorical column
    """

    global ENCODERS

    for column in CATEGORICAL_PROPS:
        if column not in ENCODERS:
            print(f"Creating encoder for column: {column}")
            # Simply set all zeros if the category is unseen
            encoder = OneHotEncoder(handle_unknown="ignore")
            encoder.fit(df[column].values.reshape(-1, 1))
            ENCODERS[column] = encoder


def preprocess_data(df):
    """Filter dataframe to include only useful features and apply categorical one hot encoders

    Args:
        df (pd.DataFrame): Pandas dataframe to apply transforms to
    """
    global ENCODERS

    useful_props = [
        "amt",
        "age",
        "merch_lat",
        "merch_long",
        "category",
        "region",
        "gender",
        "state",
        "lat",
        "long",
        "city_pop",
        "job",
        "trans_date_trans_time",
        "is_fraud",
    ]
    categorical = ["category", "region", "gender", "state", "job"]

    df.loc[:, "age"] = (pd.Timestamp.now() - pd.to_datetime(df["dob"])) // pd.Timedelta(
        "1y"
    )

    # Filter only useful columns
    df = df[useful_props]

    for column in categorical:
        encoder = ENCODERS.get(column)
        encoded_data = encoder.transform(df[column].values.reshape(-1, 1)).toarray()
        encoded_df = pd.DataFrame(
            encoded_data,
            columns=[
                column + "_" + "_".join(x.split("_")[1:])
                for x in encoder.get_feature_names()
            ],
        )
        encoded_df.index = df.index
        df = df.join(encoded_df).drop(column, axis=1)

    return df


def get_key_vault() -> Keyvault:
    """Retreives keyvault from current run"""
    run: Run = Run.get_context()
    logging.info(f"Got run context: {run}")
    workspace: Workspace = run.experiment.workspace
    return workspace.get_default_keyvault()


def download_kaggle_dataset(kaggle_client, path):
    """Downloads datasets to specified location

    Args:
        kaggle_client (KaggleApi): Instance of KaggleApi to use for retrieving the dataset
        path(str): location where to store downloaded dataset
    """
    kaggle_client.dataset_download_files("kartik2112/fraud-detection", path=path)


def run(args):
    """Run script with arguments (the core of the component).

    Args:
        args (argparse.namespace): command line arguments provided to script
    """

    if args.silo_count < 1 or args.silo_count > 4:
        raise Exception("Number of splits/silos must be between 1 and 4 (included)!")

    kv = get_key_vault()
    kaggle_client = get_kaggle_client(kv)
    download_kaggle_dataset(kaggle_client, "./dataset")

    with ZipFile("./dataset/fraud-detection.zip", "r") as zObject:
        zObject.extractall("./dataset/extracted")

    df_train = pd.read_csv("./dataset/extracted/fraudTrain.csv", index_col=0)
    print(f"Loaded train dataset with {len(df_train)} rows")
    df_test = pd.read_csv("./dataset/extracted/fraudTest.csv", index_col=0)
    print(f"Loaded test dataset with {len(df_train)} rows")
    regions_df = pd.read_csv("./us_regions.csv")
    state_region = {row.StateCode: row.Region for row in regions_df.itertuples()}
    print(f"Loaded state/regions:\n {state_region}")

    df_train.loc[:, "region"] = df_train["state"].map(state_region)
    df_test.loc[:, "region"] = df_test["state"].map(state_region)

    # Create categorical encoder before any further preprocessing/reduction
    fit_encoders(df_train)
    df_train = preprocess_data(df_train)
    df_test = preprocess_data(df_test)

    columns_per_silo = len(df_train.columns)//args.silo_count
    train_path = f"{args.raw_train_data}/train.csv"
    test_path = f"{args.raw_test_data}/test.csv"

    if args.silo_index == 0:
        train_data_filtered = df_train[["is_fraud"]]
        test_data_filtered = df_test[["is_fraud"]]
    elif args.silo_index == args.silo_count - 1:
        train_data_filtered = df_train[df_train.columns[(args.silo_index-1)*columns_per_silo:-1]]
        test_data_filtered = df_test[df_test.columns[(args.silo_index-1)*columns_per_silo:-1]]
    else:
        train_data_filtered = df_train[df_train.columns[(args.silo_index-1)*columns_per_silo: args.silo_index*columns_per_silo]]
        test_data_filtered = df_test[df_test.columns[(args.silo_index-1)*columns_per_silo: args.silo_index*columns_per_silo]]

    print(f"Filtered train dataset has {len(train_data_filtered)} rows and {len(train_data_filtered.columns)} columns: {list(train_data_filtered.columns)}")
    print(f"Filtered test dataset has {len(test_data_filtered)} rows and {len(test_data_filtered.columns)} columns: {list(test_data_filtered.columns)}")

    train_data_filtered.to_csv(train_path, index=False)
    test_data_filtered.to_csv(test_path, index=False)


def get_arg_parser(parser=None):
    """Parse the command line arguments for merge using argparse.

    Args:
        parser (argparse.ArgumentParser or CompliantArgumentParser):
        an argument parser instance

    Returns:
        ArgumentParser: the argument parser instance

    Notes:
        if parser is None, creates a new parser instance
    """
    # add arguments that are specific to the component
    if parser is None:
        parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--silo_count",
        type=int,
        required=True,
        help="Number of silos",
    )
    parser.add_argument(
        "--silo_index",
        type=int,
        required=True,
        help="Index of the current silo",
    )
    parser.add_argument(
        "--raw_train_data",
        type=str,
        required=True,
        help="Output folder for train data",
    )
    parser.add_argument(
        "--raw_test_data",
        type=str,
        required=True,
        help="Output folder for test data",
    )
    return parser


def main(cli_args=None):
    """Component main function.

    It parses arguments and executes run() with the right arguments.

    Args:
        cli_args (List[str], optional): list of args to feed script, useful for debugging. Defaults to None.
    """

    # build an arg parser
    parser = get_arg_parser()

    # run the parser on cli args
    args = parser.parse_args(cli_args)

    print(f"Running script with arguments: {args}")
    run(args)


if __name__ == "__main__":

    # Set logging to sys.out
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    log_format = logging.Formatter("[%(asctime)s] [%(levelname)s] - %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(log_format)
    logger.addHandler(handler)

    main()