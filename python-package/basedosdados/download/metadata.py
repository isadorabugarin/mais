from google.cloud import bigquery
import pandas as pd
import requests

from basedosdados.download.base import credentials

def _safe_fetch(url:str):
    """
    Safely fetchs urls and, if somehting goes wrong, informs user what is the possible cause
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as err:
        print ("This url doesn't appear to exists:",err)
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)   

def _fix_size(s, step=80):

    final = ""

    for l in s.split(" "):
        final += (l + " ") if len(final.split("\n")[-1]) < step else "\n"

    return final


def _print_output(df):
    """Prints dataframe contents as print blocks
    Args:
        df (pd.DataFrame): table to be printed
    """

    columns = df.columns
    step = 80
    print()
    for i, row in df.iterrows():
        for c in columns:
            print(_fix_size(f"{c}: \n\t{row[c]}"))
        print("-" * (step + 15))
    print()


def _handle_output(verbose, output_type, df, col_name=None):
    """Handles datasets and tables listing outputs based on user's choice.
    Either prints it to the screen or returns it as a `list` object.
    Args:
        verbose (bool): amount of verbosity
        output_type (str): type of output
        df (pd.DataFrame, bigquery.Dataset or bigquery.Table): table containing datasets metadata
        col_name (str): name of column with id's data
    """

    df_is_dataframe = type(df) == pd.DataFrame
    df_is_bq_dataset_or_table = type(df) == bigquery.Table
    df_is_bq_dataset_or_table |= type(df) == bigquery.Dataset

    if verbose == True and df_is_dataframe:
        _print_output(df)

    elif verbose == True and df_is_bq_dataset_or_table:
        print(df.description)

    elif verbose == False:
        if output_type == "list":
            return df[col_name].to_list()
        elif output_type == "str":
            return df.description
        elif output_type == "records":
            return df.to_dict("records")
        else:
            msg = '`output_type` argument must be set to "list", "str" or "records".'
            raise ValueError(msg)

    else:
        raise TypeError("`verbose` argument must be of `bool` type.")

    return None

def list_datasets(query, limit=10, with_description=False, verbose=True):
    """
    This function uses `bd_dataset_search` website API
    enpoint to retrieve a list of available datasets.

    Args:
        query (str):
            String to search in datasets' metadata.
        limit (int):
            Field to limit the number of results
        with_description (bool): Optional
            If True, fetch short dataset description for each dataset.
        verbose (bool): Optional.
            If set to True, information is printed to the screen. If set to False, a list object is returned.

    Returns:
        list | stdout
    """

    url = f"https://basedosdados.org/api/3/action/bd_dataset_search?q={query}&page_size={limit}&resource_type=bdm_table"

    response = _safe_fetch(url)

    json_response = response.json()

    # this dict has all information we need to output the function
    dataset_dict = {
        "dataset_id": [
            dataset["name"] for dataset in json_response["result"]["datasets"]
        ],
        "description": [
            dataset["notes"] if "notes" in dataset.keys() else None
            for dataset in json_response["result"]["datasets"]
        ],
    }

    # select desired output using dataset_id info. Note that the output is either a standardized string or a list
    if verbose & (with_description == False):
        return _print_output(pd.DataFrame.from_dict(dataset_dict)[["dataset_id"]])
    elif verbose & with_description:
        return _print_output(
            pd.DataFrame.from_dict(dataset_dict)[["dataset_id", "description"]]
        )
    elif (verbose == False) & (with_description == False):
        return dataset_dict["dataset_id"]
    elif (verbose == False) & with_description:
        return [
            {
                "dataset_id": dataset_dict["dataset_id"][k],
                "description": dataset_dict["description"][k],
            }
            for k in range(len(dataset_dict["dataset_id"]))
        ]


def list_dataset_tables(
    dataset_id,
    with_description=False,
    verbose=True,
):
    """
    Fetch table_id for tables available at the specified dataset_id. Prints the information on screen or returns it as a list.

    Args:
        dataset_id (str): Optional.
            Dataset id returned by list_datasets function
        limit (int):
            Field to limit the number of results
        with_description (bool): Optional
             If True, fetch short table descriptions for each table that match the search criteria.
        verbose (bool): Optional.
            If set to True, information is printed to the screen. If set to False, a list object is returned.

    Returns:
        stdout | list
    """

    dataset_id = dataset_id.replace("-","_") #The dataset_id pattern in the bd_dataset_search endpoint response uses a hyphen as a separator, while in the endpoint urls that specify the dataset_id parameter the separator used is an underscore. See issue #1079

    url = f"https://basedosdados.org/api/3/action/bd_bdm_dataset_show?dataset_id={dataset_id}"

    response = _safe_fetch(url)

    json_response = response.json()

    dataset = json_response["result"]
    # this dict has all information need to output the function
    table_dict = {
        "table_id": [
            dataset["resources"][k]["name"] for k in range(len(dataset["resources"]))
        ],
        "description": [
            dataset["resources"][k]["description"]
            for k in range(len(dataset["resources"]))
        ],
    }
    # select desired output using table_id info. Note that the output is either a standardized string or a list
    if verbose & (with_description == False):
        return _print_output(pd.DataFrame.from_dict(table_dict)[["table_id"]])
    elif verbose & with_description:
        return _print_output(
            pd.DataFrame.from_dict(table_dict)[["table_id", "description"]]
        )
    elif (verbose == False) & (with_description == False):
        return table_dict["table_id"]
    elif (verbose == False) & with_description:
        return [
            {
                "table_id": table_dict["table_id"][k],
                "description": table_dict["description"][k],
            }
            for k in range(len(table_dict["table_id"]))
        ]


def get_dataset_description(
    dataset_id,
    verbose=True,
):
    """
    Prints the full dataset description.

    Args:
        dataset_id (str): Required.
            Dataset id available in list_datasets.
        verbose (bool): Optional.
            If set to True, information is printed to the screen. If set to False, data is returned as a `str`.

    Returns:
        stdout | str
    """
    url = f"https://basedosdados.org/api/3/action/bd_bdm_dataset_show?dataset_id={dataset_id}"

    response = _safe_fetch(url)

    json_response = response.json()

    description = json_response["result"]["notes"]

    if verbose:
        print(description)
    else:
        return description


def get_table_description(
    dataset_id,
    table_id,
    verbose=True,
):
    """
    Prints the full table description.

    Args:
        dataset_id (str): Required.
            Dataset id available in list_datasets.
        table_id (str): Required.
            Table id available in list_dataset_tables
        verbose (bool): Optional.
            If set to True, information is printed to the screen. If set to False, data is returned as a `str`.

    Returns:
        stdout | str
    """

    url = f"https://basedosdados.org/api/3/action/bd_bdm_table_show?dataset_id={dataset_id}&table_id={table_id}"

    response = _safe_fetch(url)

    json_response = response.json()

    description = json_response["result"]["description"]

    if verbose:
        print(description)
    else:
        return description


def get_table_columns(
    dataset_id,
    table_id,
    verbose=True,
):

    """
        Fetch the names, types and descriptions for the columns in the specified table. Prints
        information on screen.
    Args:
        dataset_id (str): Required.
            Dataset id available in list_datasets.
        table_id (str): Required.
            Table id available in list_dataset_tables
        verbose (bool): Optional.
            If set to True, information is printed to the screen. If set to False, data is returned as a `list` of `dict`s.

    Returns:
        stdout | list
    """

    url = f"https://basedosdados.org/api/3/action/bd_bdm_table_show?dataset_id={dataset_id}&table_id={table_id}"

    response = _safe_fetch(url)

    json_response = response.json()

    columns = json_response["result"]["columns"]

    if verbose:
        _print_output(pd.DataFrame(columns))
    else:
        return columns


def get_table_size(
    dataset_id,
    table_id,
    verbose=True,
):
    """Use a query to get the number of rows and size (in Mb) of a table.

    WARNING: this query may cost a lot depending on the table.

    Args:
        dataset_id (str): Optional.
            Dataset id available in basedosdados. It should always come with table_id.
        table_id (str): Optional.
            Table id available in basedosdados.dataset_id.
            It should always come with dataset_id.
        verbose (bool): Optional.
            If set to True, information is printed to the screen. If set to False, data is returned as a `list` of `dict`s.
    """
    url = f"https://basedosdados.org/api/3/action/bd_bdm_table_show?dataset_id={dataset_id}&table_id={table_id}"

    response = _safe_fetch(url)

    json_response = response.json()

    size = json_response["result"]["size"]

    if size==None:
        print("Size not available")
    else:
        if verbose:
            _print_output(pd.DataFrame(size))
        else:
            return size
def search(query, order_by):
    """This function works as a wrapper to the `bd_dataset_search` website API
    enpoint.

    Args:
        query (str):
            String to search in datasets and tables' metadata.
        order_by (str): score|popular|recent
            Field by which the results will be ordered.

    Returns:
        pd.DataFrame:
            Response from the API presented as a pandas DataFrame. Each row is
            a table. Each column is a field identifying the table.
    """

    # validate order_by input
    if order_by not in ["score", "popular", "recent"]:
        raise ValueError(
            f'order_by must be score, popular or recent. Received "{order_by}"'
        )

    url = f"https://basedosdados.org/api/3/action/bd_dataset_search?q={query}&order_by={order_by}&resource_type=bdm_table"

    response = _safe_fetch(url)

    json_response = response.json()

    dataset_dfs = []
    # first loop identify the number of the tables in each datasets
    for dataset in json_response["result"]["datasets"]:
        tables_dfs = []
        len(dataset["resources"])
        # second loop extracts tables' information for each dataset
        for table in dataset["resources"]:
            data_table = pd.DataFrame(
                {k: str(table[k]) for k in list(table.keys())}, index=[0]
            )
            tables_dfs.append(data_table)
        # append tables' dataframes for each dataset
        data_ds = tables_dfs[0].append(tables_dfs[1:]).reset_index(drop=True)
        dataset_dfs.append(data_ds)
    # append datasets' dataframes
    df = dataset_dfs[0].append(dataset_dfs[1:]).reset_index(drop=True)

    return df