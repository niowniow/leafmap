import os
import pystac
import requests


class TitilerEndpoint:
    """This class contains the methods for the titiler endpoint."""

    def __init__(
        self,
        endpoint="https://titiler.xyz",
        name="stac",
        TileMatrixSetId="WebMercatorQuad",
    ):
        """Initialize the TitilerEndpoint object.

        Args:
            endpoint (str, optional): The endpoint of the titiler server. Defaults to "https://titiler.xyz".
            name (str, optional): The name to be used in the file path. Defaults to "stac".
            TileMatrixSetId (str, optional): The TileMatrixSetId to be used in the file path. Defaults to "WebMercatorQuad".
        """
        self.endpoint = endpoint
        self.name = name
        self.TileMatrixSetId = TileMatrixSetId

    def url_for_stac_item(self):
        return f"{self.endpoint}/{self.name}/{self.TileMatrixSetId}/tilejson.json"

    def url_for_stac_assets(self):
        return f"{self.endpoint}/{self.name}/assets"

    def url_for_stac_bounds(self):
        return f"{self.endpoint}/{self.name}/bounds"

    def url_for_stac_info(self):
        return f"{self.endpoint}/{self.name}/info"

    def url_for_stac_info_geojson(self):
        return f"{self.endpoint}/{self.name}/info.geojson"

    def url_for_stac_statistics(self):
        return f"{self.endpoint}/{self.name}/statistics"

    def url_for_stac_pixel_value(self, lon, lat):
        return f"{self.endpoint}/{self.name}/point/{lon},{lat}"

    def url_for_stac_wmts(self):
        return (
            f"{self.endpoint}/{self.name}/{self.TileMatrixSetId}/WMTSCapabilities.xml"
        )


class PlanetaryComputerEndpoint(TitilerEndpoint):
    """This class contains the methods for the Microsoft Planetary Computer endpoint."""

    def __init__(
        self,
        endpoint="https://planetarycomputer.microsoft.com/api/data/v1",
        name="item",
        TileMatrixSetId="WebMercatorQuad",
    ):
        """Initialize the PlanetaryComputerEndpoint object.

        Args:
            endpoint (str, optional): The endpoint of the titiler server. Defaults to "https://planetarycomputer.microsoft.com/api/data/v1".
            name (str, optional): The name to be used in the file path. Defaults to "item".
            TileMatrixSetId (str, optional): The TileMatrixSetId to be used in the file path. Defaults to "WebMercatorQuad".
        """
        super().__init__(endpoint, name, TileMatrixSetId)

    def url_for_stac_collection(self):
        return f"{self.endpoint}/collection/{self.TileMatrixSetId}/tilejson.json"

    def url_for_collection_assets(self):
        return f"{self.endpoint}/collection/assets"

    def url_for_collection_bounds(self):
        return f"{self.endpoint}/collection/bounds"

    def url_for_collection_info(self):
        return f"{self.endpoint}/collection/info"

    def url_for_collection_info_geojson(self):
        return f"{self.endpoint}/collection/info.geojson"

    def url_for_collection_pixel_value(self, lon, lat):
        return f"{self.endpoint}/collection/point/{lon},{lat}"

    def url_for_collection_wmts(self):
        return f"{self.endpoint}/collection/{self.TileMatrixSetId}/WMTSCapabilities.xml"

    def url_for_collection_lat_lon_assets(self, lng, lat):
        return f"{self.endpoint}/collection/{lng},{lat}/assets"

    def url_for_collection_bbox_assets(self, minx, miny, maxx, maxy):
        return f"{self.endpoint}/collection/{minx},{miny},{maxx},{maxy}/assets"

    def url_for_stac_mosaic(self, searchid):
        return f"{self.endpoint}/mosaic/{searchid}/{self.TileMatrixSetId}/tilejson.json"

    def url_for_mosaic_info(self, searchid):
        return f"{self.endpoint}/mosaic/{searchid}/info"

    def url_for_mosaic_lat_lon_assets(self, searchid, lon, lat):
        return f"{self.endpoint}/mosaic/{searchid}/{lon},{lat}/assets"


def check_titiler_endpoint(titiler_endpoint=None):
    """Returns the default titiler endpoint.

    Returns:
        object: A titiler endpoint.
    """
    if titiler_endpoint is None:
        if os.environ.get("TITILER_ENDPOINT") is not None:
            titiler_endpoint = os.environ.get("TITILER_ENDPOINT")

            if titiler_endpoint == "planetary-computer":
                titiler_endpoint = PlanetaryComputerEndpoint()
        else:
            titiler_endpoint = "https://titiler.xyz"
    elif titiler_endpoint in ["planetary-computer", "pc"]:
        titiler_endpoint = PlanetaryComputerEndpoint()

    return titiler_endpoint


def cog_tile(url, bands=None, titiler_endpoint=None, **kwargs):
    """Get a tile layer from a Cloud Optimized GeoTIFF (COG).
        Source code adapted from https://developmentseed.org/titiler/examples/notebooks/Working_with_CloudOptimizedGeoTIFF_simple/

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        bands (list, optional): List of bands to use. Defaults to None.
        titiler_endpoint (str, optional): TiTiler endpoint. Defaults to "https://titiler.xyz".
        **kwargs: Additional arguments to pass to the titiler endpoint. For more information about the available arguments, see https://developmentseed.org/titiler/endpoints/cog/#tiles.
            For example, to apply a rescaling to multiple bands, use something like `rescale=["164,223","130,211","99,212"]`.

    Returns:
        tuple: Returns the COG Tile layer URL and bounds.
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)

    kwargs["url"] = url

    band_names = cog_bands(url, titiler_endpoint)

    if isinstance(bands, str):
        bands = [bands]

    if bands is None and "bidx" not in kwargs:
        if len(band_names) >= 3:
            kwargs["bidx"] = [1, 2, 3]
    elif isinstance(bands, list) and "bidx" not in kwargs:
        if all(isinstance(x, int) for x in bands):
            if len(set(bands)) == 1:
                bands = bands[0]
            kwargs["bidx"] = bands
        elif all(isinstance(x, str) for x in bands):
            if len(set(bands)) == 1:
                bands = bands[0]
            kwargs["bidx"] = [band_names.index(x) + 1 for x in bands]
        else:
            raise ValueError("Bands must be a list of integers or strings.")

    if "palette" in kwargs:
        kwargs["colormap_name"] = kwargs["palette"].lower()
        del kwargs["palette"]

    if "bidx" not in kwargs:
        kwargs["bidx"] = [1]
    elif isinstance(kwargs["bidx"], int):
        kwargs["bidx"] = [kwargs["bidx"]]

    if "rescale" not in kwargs:
        stats = cog_stats(url, titiler_endpoint)

        if "message" not in stats:
            try:
                rescale = []
                for i in band_names:
                    rescale.append(
                        "{},{}".format(
                            stats[i]["percentile_2"],
                            stats[i]["percentile_98"],
                        )
                    )
                kwargs["rescale"] = rescale
            except Exception as e:
                print(e)

    TileMatrixSetId = "WebMercatorQuad"
    if "TileMatrixSetId" in kwargs.keys():
        TileMatrixSetId = kwargs["TileMatrixSetId"]
        kwargs.pop("TileMatrixSetId")

    r = requests.get(
        f"{titiler_endpoint}/cog/{TileMatrixSetId}/tilejson.json", params=kwargs
    ).json()
    return r["tiles"][0]


def cog_tile_vmin_vmax(
    url, bands=None, titiler_endpoint=None, percentile=True, **kwargs
):
    """Get a tile layer from a Cloud Optimized GeoTIFF (COG) and return the minimum and maximum values.

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        bands (list, optional): List of bands to use. Defaults to None.
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".
        percentile (bool, optional): Whether to use percentiles or not. Defaults to True.
    Returns:
        tuple: Returns the minimum and maximum values.
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    stats = cog_stats(url, titiler_endpoint)

    if isinstance(bands, str):
        bands = [bands]

    if bands is not None:
        stats = {s: stats[s] for s in stats if s in bands}

    if percentile:
        vmin = min([stats[s]["percentile_2"] for s in stats])
        vmax = max([stats[s]["percentile_98"] for s in stats])
    else:
        vmin = min([stats[s]["min"] for s in stats])
        vmax = max([stats[s]["max"] for s in stats])

    return vmin, vmax


def cog_mosaic(
    links,
    titiler_endpoint=None,
    username="anonymous",
    layername=None,
    overwrite=False,
    verbose=True,
    **kwargs,
):
    """Creates a COG mosaic from a list of COG URLs.

    Args:
        links (list): A list containing COG HTTP URLs.
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".
        username (str, optional): User name for the titiler endpoint. Defaults to "anonymous".
        layername ([type], optional): Layer name to use. Defaults to None.
        overwrite (bool, optional): Whether to overwrite the layer name if existing. Defaults to False.
        verbose (bool, optional): Whether to print out descriptive information. Defaults to True.

    Raises:
        Exception: If the COG mosaic fails to create.

    Returns:
        str: The tile URL for the COG mosaic.
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if layername is None:
        layername = "layer_X"

    try:
        if verbose:
            print("Creating COG masaic ...")

        # Create token
        r = requests.post(
            f"{titiler_endpoint}/tokens/create",
            json={"username": username, "scope": ["mosaic:read", "mosaic:create"]},
        ).json()
        token = r["token"]

        # Create mosaic
        requests.post(
            f"{titiler_endpoint}/mosaicjson/create",
            json={
                "username": username,
                "layername": layername,
                "files": links,
                # "overwrite": overwrite
            },
            params={
                "access_token": token,
            },
        ).json()

        r2 = requests.get(
            f"{titiler_endpoint}/mosaicjson/{username}.{layername}/tilejson.json",
        ).json()

        return r2["tiles"][0]

    except Exception as e:
        raise Exception(e)


def cog_mosaic_from_file(
    filepath,
    skip_rows=0,
    titiler_endpoint=None,
    username="anonymous",
    layername=None,
    overwrite=False,
    verbose=True,
    **kwargs,
):
    """Creates a COG mosaic from a csv/txt file stored locally for through HTTP URL.

    Args:
        filepath (str): Local path or HTTP URL to the csv/txt file containing COG URLs.
        skip_rows (int, optional): The number of rows to skip in the file. Defaults to 0.
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".
        username (str, optional): User name for the titiler endpoint. Defaults to "anonymous".
        layername ([type], optional): Layer name to use. Defaults to None.
        overwrite (bool, optional): Whether to overwrite the layer name if existing. Defaults to False.
        verbose (bool, optional): Whether to print out descriptive information. Defaults to True.

    Returns:
        str: The tile URL for the COG mosaic.
    """
    import urllib

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    links = []
    if filepath.startswith("http"):
        data = urllib.request.urlopen(filepath)
        for line in data:
            links.append(line.decode("utf-8").strip())

    else:
        with open(filepath) as f:
            links = [line.strip() for line in f.readlines()]

    links = links[skip_rows:]
    # print(links)
    mosaic = cog_mosaic(
        links, titiler_endpoint, username, layername, overwrite, verbose, **kwargs
    )
    return mosaic


def cog_bounds(url, titiler_endpoint=None):
    """Get the bounding box of a Cloud Optimized GeoTIFF (COG).

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".

    Returns:
        list: A list of values representing [left, bottom, right, top]
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    r = requests.get(f"{titiler_endpoint}/cog/bounds", params={"url": url}).json()

    if "bounds" in r.keys():
        bounds = r["bounds"]
    else:
        bounds = None
    return bounds


def cog_center(url, titiler_endpoint=None):
    """Get the centroid of a Cloud Optimized GeoTIFF (COG).

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".

    Returns:
        tuple: A tuple representing (longitude, latitude)
    """
    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    bounds = cog_bounds(url, titiler_endpoint)
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)  # (lat, lon)
    return center


def cog_bands(url, titiler_endpoint=None):
    """Get band names of a Cloud Optimized GeoTIFF (COG).

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".

    Returns:
        list: A list of band names
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    r = requests.get(
        f"{titiler_endpoint}/cog/info",
        params={
            "url": url,
        },
    ).json()

    bands = [b[0] for b in r["band_descriptions"]]
    return bands


def cog_stats(url, titiler_endpoint=None):
    """Get band statistics of a Cloud Optimized GeoTIFF (COG).

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".

    Returns:
        list: A dictionary of band statistics.
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    r = requests.get(
        f"{titiler_endpoint}/cog/statistics",
        params={
            "url": url,
        },
    ).json()

    return r


def cog_info(url, titiler_endpoint=None, return_geojson=False):
    """Get band statistics of a Cloud Optimized GeoTIFF (COG).

    Args:
        url (str): HTTP URL to a COG, e.g., https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif
        titiler_endpoint (str, optional): Titiler endpoint. Defaults to "https://titiler.xyz".

    Returns:
        list: A dictionary of band info.
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    info = "info"
    if return_geojson:
        info = "info.geojson"

    r = requests.get(
        f"{titiler_endpoint}/cog/{info}",
        params={
            "url": url,
        },
    ).json()

    return r


def cog_pixel_value(
    lon,
    lat,
    url,
    bidx=None,
    titiler_endpoint=None,
    verbose=True,
    **kwargs,
):
    """Get pixel value from COG.

    Args:
        lon (float): Longitude of the pixel.
        lat (float): Latitude of the pixel.
        url (str): HTTP URL to a COG, e.g., 'https://opendata.digitalglobe.com/events/california-fire-2020/pre-event/2018-02-16/pine-gulch-fire20/1030010076004E00.tif'
        bidx (str, optional): Dataset band indexes (e.g bidx=1, bidx=1&bidx=2&bidx=3). Defaults to None.
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.
        verbose (bool, optional): Print status messages. Defaults to True.

    Returns:
        list: A dictionary of band info.
    """

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    kwargs["url"] = url
    if bidx is not None:
        kwargs["bidx"] = bidx

    r = requests.get(f"{titiler_endpoint}/cog/point/{lon},{lat}", params=kwargs).json()
    bands = cog_bands(url, titiler_endpoint)
    # if isinstance(titiler_endpoint, str):
    #     r = requests.get(f"{titiler_endpoint}/cog/point/{lon},{lat}", params=kwargs).json()
    # else:
    #     r = requests.get(
    #         titiler_endpoint.url_for_stac_pixel_value(lon, lat), params=kwargs
    #     ).json()

    if "detail" in r:
        if verbose:
            print(r["detail"])
        return None
    else:
        values = r["values"]
        result = dict(zip(bands, values))
        return result


def stac_tile(
    url=None,
    collection=None,
    item=None,
    assets=None,
    bands=None,
    titiler_endpoint=None,
    **kwargs,
):

    """Get a tile layer from a single SpatialTemporal Asset Catalog (STAC) item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        assets (str | list): The Microsoft Planetary Computer STAC asset ID, e.g., ["SR_B7", "SR_B5", "SR_B4"].
        bands (list): A list of band names, e.g., ["SR_B7", "SR_B5", "SR_B4"]
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "https://planetarycomputer.microsoft.com/api/data/v1", "planetary-computer", "pc". Defaults to None.

    Returns:
        str: Returns the STAC Tile layer URL.
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item

    if "palette" in kwargs:
        kwargs["colormap_name"] = kwargs["palette"].lower()
        del kwargs["palette"]

    if isinstance(bands, list) and len(set(bands)) == 1:
        bands = bands[0]

    if isinstance(assets, list) and len(set(assets)) == 1:
        assets = assets[0]

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)

    if isinstance(titiler_endpoint, PlanetaryComputerEndpoint):
        if isinstance(bands, str):
            bands = bands.split(",")
        if isinstance(assets, str):
            assets = assets.split(",")
        if assets is None and (bands is not None):
            assets = bands
        else:
            kwargs["bidx"] = bands

        kwargs["assets"] = assets

        if (
            (assets is not None)
            and ("asset_expression" not in kwargs)
            and ("expression" not in kwargs)
            and ("rescale" not in kwargs)
        ):
            stats = stac_stats(
                collection=collection,
                item=item,
                assets=assets,
                titiler_endpoint=titiler_endpoint,
            )
            if "detail" not in stats:

                try:
                    percentile_2 = min([stats[s]["percentile_2"] for s in stats])
                    percentile_98 = max([stats[s]["percentile_98"] for s in stats])
                except:
                    percentile_2 = min(
                        [
                            stats[s][list(stats[s].keys())[0]]["percentile_2"]
                            for s in stats
                        ]
                    )
                    percentile_98 = max(
                        [
                            stats[s][list(stats[s].keys())[0]]["percentile_98"]
                            for s in stats
                        ]
                    )
                kwargs["rescale"] = f"{percentile_2},{percentile_98}"
            else:
                print(stats["detail"])  # When operation times out.

    else:
        if isinstance(bands, str):
            bands = bands.split(",")
        if isinstance(assets, str):
            assets = assets.split(",")

        if assets is None:
            if bands is not None:
                assets = bands
            else:
                bnames = stac_bands(url)
                if len(bnames) >= 3:
                    assets = bnames[0:3]
                else:
                    assets = bnames[0]
        else:
            kwargs["asset_bidx"] = bands
        kwargs["assets"] = assets

    TileMatrixSetId = "WebMercatorQuad"
    if "TileMatrixSetId" in kwargs.keys():
        TileMatrixSetId = kwargs["TileMatrixSetId"]
        kwargs.pop("TileMatrixSetId")

    if isinstance(titiler_endpoint, str):
        r = requests.get(
            f"{titiler_endpoint}/stac/{TileMatrixSetId}/tilejson.json",
            params=kwargs,
        ).json()
    else:
        r = requests.get(titiler_endpoint.url_for_stac_item(), params=kwargs).json()

    return r["tiles"][0]


def stac_bounds(url=None, collection=None, item=None, titiler_endpoint=None, **kwargs):
    """Get the bounding box of a single SpatialTemporal Asset Catalog (STAC) item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        list: A list of values representing [left, bottom, right, top]
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/bounds", params=kwargs).json()
    else:
        r = requests.get(titiler_endpoint.url_for_stac_bounds(), params=kwargs).json()

    bounds = r["bounds"]
    return bounds


def stac_center(url=None, collection=None, item=None, titiler_endpoint=None, **kwargs):
    """Get the centroid of a single SpatialTemporal Asset Catalog (STAC) item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        tuple: A tuple representing (longitude, latitude)
    """
    bounds = stac_bounds(url, collection, item, titiler_endpoint, **kwargs)
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)  # (lon, lat)
    return center


def stac_bands(url=None, collection=None, item=None, titiler_endpoint=None, **kwargs):
    """Get band names of a single SpatialTemporal Asset Catalog (STAC) item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        list: A list of band names
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/assets", params=kwargs).json()
    else:
        r = requests.get(titiler_endpoint.url_for_stac_assets(), params=kwargs).json()

    return r


def stac_stats(
    url=None, collection=None, item=None, assets=None, titiler_endpoint=None, **kwargs
):
    """Get band statistics of a STAC item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        assets (str | list): The Microsoft Planetary Computer STAC asset ID, e.g., ["SR_B7", "SR_B5", "SR_B4"].
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        list: A dictionary of band statistics.
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item
    if assets is not None:
        kwargs["assets"] = assets

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/statistics", params=kwargs).json()
    else:
        r = requests.get(
            titiler_endpoint.url_for_stac_statistics(), params=kwargs
        ).json()

    return r


def stac_info(
    url=None, collection=None, item=None, assets=None, titiler_endpoint=None, **kwargs
):
    """Get band info of a STAC item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        assets (str | list): The Microsoft Planetary Computer STAC asset ID, e.g., ["SR_B7", "SR_B5", "SR_B4"].
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        list: A dictionary of band info.
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item
    if assets is not None:
        kwargs["assets"] = assets

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/info", params=kwargs).json()
    else:
        r = requests.get(titiler_endpoint.url_for_stac_info(), params=kwargs).json()

    return r


def stac_info_geojson(
    url=None, collection=None, item=None, assets=None, titiler_endpoint=None, **kwargs
):
    """Get band info of a STAC item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        assets (str | list): The Microsoft Planetary Computer STAC asset ID, e.g., ["SR_B7", "SR_B5", "SR_B4"].
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        list: A dictionary of band info.
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item
    if assets is not None:
        kwargs["assets"] = assets

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/info.geojson", params=kwargs).json()
    else:
        r = requests.get(
            titiler_endpoint.url_for_stac_info_geojson(), params=kwargs
        ).json()

    return r


def stac_assets(url=None, collection=None, item=None, titiler_endpoint=None, **kwargs):
    """Get all assets of a STAC item.

    Args:
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.

    Returns:
        list: A list of assets.
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/assets", params=kwargs).json()
    else:
        r = requests.get(titiler_endpoint.url_for_stac_assets(), params=kwargs).json()

    return r


def stac_pixel_value(
    lon,
    lat,
    url=None,
    collection=None,
    item=None,
    assets=None,
    titiler_endpoint=None,
    verbose=True,
    **kwargs,
):
    """Get pixel value from STAC assets.

    Args:
        lon (float): Longitude of the pixel.
        lat (float): Latitude of the pixel.
        url (str): HTTP URL to a STAC item, e.g., https://canada-spot-ortho.s3.amazonaws.com/canada_spot_orthoimages/canada_spot5_orthoimages/S5_2007/S5_11055_6057_20070622/S5_11055_6057_20070622.json
        collection (str): The Microsoft Planetary Computer STAC collection ID, e.g., landsat-8-c2-l2.
        item (str): The Microsoft Planetary Computer STAC item ID, e.g., LC08_L2SP_047027_20201204_02_T1.
        assets (str | list): The Microsoft Planetary Computer STAC asset ID, e.g., ["SR_B7", "SR_B5", "SR_B4"].
        titiler_endpoint (str, optional): Titiler endpoint, e.g., "https://titiler.xyz", "planetary-computer", "pc". Defaults to None.
        verbose (bool, optional): Print out the error message. Defaults to True.

    Returns:
        list: A dictionary of pixel values for each asset.
    """

    if url is None and collection is None:
        raise ValueError("Either url or collection must be specified.")

    if collection is not None and titiler_endpoint is None:
        titiler_endpoint = "planetary-computer"

    if url is not None:
        kwargs["url"] = url
    if collection is not None:
        kwargs["collection"] = collection
    if item is not None:
        kwargs["item"] = item

    if assets is None:
        assets = stac_assets(
            url=url,
            collection=collection,
            item=item,
            titiler_endpoint=titiler_endpoint,
        )
        assets = ",".join(assets)
    kwargs["assets"] = assets

    titiler_endpoint = check_titiler_endpoint(titiler_endpoint)
    if isinstance(titiler_endpoint, str):
        r = requests.get(f"{titiler_endpoint}/stac/{lon},{lat}", params=kwargs).json()
    else:
        r = requests.get(
            titiler_endpoint.url_for_stac_pixel_value(lon, lat), params=kwargs
        ).json()

    if "detail" in r:
        if verbose:
            print(r["detail"])
        return None
    else:
        values = [v[0] for v in r["values"]]
        result = dict(zip(assets.split(","), values))
        return result


def stac_object_type(url):
    """Get the STAC object type.

    Args:
        url (str): The STAC object URL.

    Returns:
        str: The STAC object type, can be catalog, collection, or item.
    """
    try:
        obj = pystac.STACObject.from_file(url)

        if isinstance(obj, pystac.Collection):
            return "collection"
        elif isinstance(obj, pystac.Item):
            return "item"
        elif isinstance(obj, pystac.Catalog):
            return "catalog"

    except Exception as e:
        print(e)
        return None


def stac_root_link(url, return_col_id=False):
    """Get the root link of a STAC object.

    Args:
        url (str): The STAC object URL.
        return_col_id (bool, optional): Return the collection ID if the STAC object is a collection. Defaults to False.

    Returns:
        str: The root link of the STAC object.
    """
    collection_id = None
    try:
        obj = pystac.STACObject.from_file(url)
        if isinstance(obj, pystac.Collection):
            collection_id = obj.id
        href = obj.get_root_link().get_href()

        if not url.startswith(href):
            href = obj.get_self_href()

        if return_col_id:
            return href, collection_id
        else:
            return href

    except Exception as e:
        print(e)
        if return_col_id:
            return None, None
        else:
            return None


def stac_client(
    url,
    headers=None,
    parameters=None,
    ignore_conformance=False,
    modifier=None,
    return_col_id=False,
):
    """Get the STAC client. It wraps the pystac.Client.open() method. See
        https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.Client.open

    Args:
        url (str): The URL of a STAC Catalog.
        headers (dict, optional):  A dictionary of additional headers to use in all requests
            made to any part of this Catalog/API. Defaults to None.
        parameters (dict, optional): Optional dictionary of query string parameters to include in all requests.
            Defaults to None.
        ignore_conformance (bool, optional): Ignore any advertised Conformance Classes in this Catalog/API.
            This means that functions will skip checking conformance, and may throw an unknown error
            if that feature is not supported, rather than a NotImplementedError. Defaults to False.
        modifier (function, optional): A callable that modifies the children collection and items
            returned by this Client. This can be useful for injecting authentication parameters
            into child assets to access data from non-public sources. Defaults to None.
        return_col_id (bool, optional): Return the collection ID. Defaults to False.

    Returns:
        pystac.Client: The STAC client.
    """
    from pystac_client import Client

    collection_id = None

    try:
        root = stac_root_link(url, return_col_id=return_col_id)

        if return_col_id:
            client = Client.open(
                root[0], headers, parameters, ignore_conformance, modifier
            )
            collection_id = root[1]
            return client, collection_id
        else:
            client = Client.open(
                root, headers, parameters, ignore_conformance, modifier
            )
            return client

    except Exception as e:
        print(e)
        return None


def stac_collections(url, return_ids=False):

    """Get the collection IDs of a STAC catalog.

    Args:
        url (str): The STAC catalog URL.
        return_ids (bool, optional): Return collection IDs. Defaults to False.

    Returns:
        list: A list of collection IDs.
    """
    try:
        client = stac_client(url)
        collections = client.get_all_collections()

        if return_ids:

            return [c.id for c in collections]
        else:
            return collections

    except Exception as e:
        print(e)
        return None


def stac_search(
    url,
    method="POST",
    max_items=None,
    limit=100,
    ids=None,
    collections=None,
    bbox=None,
    intersects=None,
    datetime=None,
    query=None,
    filter=None,
    filter_lang=None,
    sortby=None,
    fields=None,
    get_collection=False,
    get_items=False,
    get_assets=False,
    get_links=False,
    get_gdf=False,
    get_info=False,
    **kwargs,
):
    """Search a STAC API. The function wraps the pysatc_client.Client.search() method. See
        https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.Client.search

    Args:
        url (str): The STAC API URL.
        method (str, optional): The HTTP method to use when making a request to the service.
            This must be either "GET", "POST", or None. If None, this will default to "POST".
            If a "POST" request receives a 405 status for the response, it will automatically
            retry with "GET" for all subsequent requests. Defaults to "POST".
        max_items (init, optional): The maximum number of items to return from the search,
            even if there are more matching results. This client to limit the total number of
            Items returned from the items(), item_collections(), and items_as_dicts methods().
            The client will continue to request pages of items until the number of max items
            is reached. This parameter defaults to 100. Setting this to None will allow iteration
            over a possibly very large number of results.. Defaults to None.
        limit (int, optional): A recommendation to the service as to the number of items to
            return per page of results. Defaults to 100.
        ids (list, optional): List of one or more Item ids to filter on. Defaults to None.
        collections (list, optional): List of one or more Collection IDs or pystac.Collection instances.
            Only Items in one of the provided Collections will be searched. Defaults to None.
        bbox (list | tuple, optional): A list, tuple, or iterator representing a bounding box of 2D
            or 3D coordinates. Results will be filtered to only those intersecting the bounding box.
            Defaults to None.
        intersects (str | dict, optional):  A string or dictionary representing a GeoJSON geometry, or
            an object that implements a __geo_interface__ property, as supported by several
            libraries including Shapely, ArcPy, PySAL, and geojson. Results filtered to only
            those intersecting the geometry. Defaults to None.
        datetime (str, optional): Either a single datetime or datetime range used to filter results.
            You may express a single datetime using a datetime.datetime instance, a RFC 3339-compliant
            timestamp, or a simple date string (see below). Instances of datetime.datetime may be either
            timezone aware or unaware. Timezone aware instances will be converted to a UTC timestamp
            before being passed to the endpoint. Timezone unaware instances are assumed to represent
            UTC timestamps. You may represent a datetime range using a "/" separated string as described
            in the spec, or a list, tuple, or iterator of 2 timestamps or datetime instances.
            For open-ended ranges, use either ".." ('2020-01-01:00:00:00Z/..', ['2020-01-01:00:00:00Z', '..'])
            or a value of None (['2020-01-01:00:00:00Z', None]). If using a simple date string,
            the datetime can be specified in YYYY-mm-dd format, optionally truncating to
            YYYY-mm or just YYYY. Simple date strings will be expanded to include the entire
            time period. Defaults to None.
        query (list, optional): List or JSON of query parameters as per the STAC API query extension.
            such as {"eo:cloud_cover":{"lt":10}}. Defaults to None.
        filter (dict, optional): JSON of query parameters as per the STAC API filter extension. Defaults to None.
        filter_lang (str, optional): Language variant used in the filter body. If filter is a dictionary
            or not provided, defaults to ‘cql2-json’. If filter is a string, defaults to cql2-text. Defaults to None.
        sortby (str | list, optional): A single field or list of fields to sort the response by.
            such as [{ 'field': 'properties.eo:cloud_cover', 'direction': 'asc' }]. Defaults to None.
        fields (list, optional): A list of fields to include in the response. Note this may result in
            invalid STAC objects, as they may not have required fields. Use items_as_dicts to avoid object
            unmarshalling errors. Defaults to None.
        get_collection (bool, optional): True to return a pystac.ItemCollection. Defaults to False.
        get_items (bool, optional): True to return a list of pystac.Item. Defaults to False.
        get_assets (bool, optional): True to return a list of pystac.Asset. Defaults to False.
        get_links (bool, optional): True to return a list of links. Defaults to False.
        get_gdf (bool, optional): True to return a GeoDataFrame. Defaults to False.
        **kwargs: Additional keyword arguments to pass to the stac_client() function.

    Returns:
        list | pystac.ItemCollection : The search results as a list of links or a pystac.ItemCollection.
    """

    client, collection_id = stac_client(url, return_col_id=True, **kwargs)

    if client is None:
        return None
    else:

        if isinstance(intersects, dict) and "geometry" in intersects:
            intersects = intersects["geometry"]

        if collection_id is not None and collections is None:
            collections = [collection_id]

        search = client.search(
            method=method,
            max_items=max_items,
            limit=limit,
            ids=ids,
            collections=collections,
            bbox=bbox,
            intersects=intersects,
            datetime=datetime,
            query=query,
            filter=filter,
            filter_lang=filter_lang,
            sortby=sortby,
            fields=fields,
        )

        if get_collection:
            return search.item_collection()
        elif get_items:
            return list(search.items())
        elif get_assets:
            assets = {}
            for item in search.items():
                assets[item.id] = {}
                for key, value in item.get_assets().items():
                    assets[item.id][key] = value.href
            return assets
        elif get_links:
            return [item.get_self_href() for item in search.items()]
        elif get_gdf:
            import geopandas as gpd

            gdf = gpd.GeoDataFrame.from_features(
                search.item_collection().to_dict(), crs="EPSG:4326"
            )
            return gdf
        elif get_info:
            items = search.items()
            info = {}
            for item in items:
                info[item.id] = {
                    "id": item.id,
                    "href": item.get_self_href(),
                    "bands": list(item.get_assets().keys()),
                    "assets": item.get_assets(),
                }
            return info
        else:
            return search


def stac_search_to_gdf(search, **kwargs):
    """Convert STAC search result to a GeoDataFrame.

    Args:
        search (pystac_client.ItemSearch): The search result returned by leafmap.stac_search().
        **kwargs: Additional keyword arguments to pass to the GeoDataFrame.from_features() function.

    Returns:
        GeoDataFrame: A GeoPandas GeoDataFrame object.
    """
    import geopandas as gpd

    gdf = gpd.GeoDataFrame.from_features(
        search.item_collection().to_dict(), crs="EPSG:4326", **kwargs
    )
    return gdf


def stac_search_to_df(search, **kwargs):
    """Convert STAC search result to a DataFrame.

    Args:
        search (pystac_client.ItemSearch): The search result returned by leafmap.stac_search().
        **kwargs: Additional keyword arguments to pass to the DataFrame.drop() function.

    Returns:
        DataFrame: A Pandas DataFrame object.
    """
    gdf = stac_search_to_gdf(search)
    return gdf.drop(columns=["geometry"], **kwargs)


def stac_search_to_dict(search, **kwargs):
    """Convert STAC search result to a dictionary.

    Args:
        search (pystac_client.ItemSearch): The search result returned by leafmap.stac_search().

    Returns:
        dict: A dictionary of STAC items, with the stac item id as the key, and the stac item as the value.
    """

    items = list(search.item_collection())
    info = {}
    for item in items:
        info[item.id] = {
            "id": item.id,
            "href": item.get_self_href(),
            "bands": list(item.get_assets().keys()),
            "assets": item.get_assets(),
        }
        links = {}
        assets = item.get_assets()
        for key, value in assets.items():
            links[key] = value.href
        info[item.id]["links"] = links
    return info


def stac_search_to_list(search, **kwargs):

    """Convert STAC search result to a list.

    Args:
        search (pystac_client.ItemSearch): The search result returned by leafmap.stac_search().

    Returns:
        list: A list of STAC items.
    """

    return search.item_collections()


def download_data_catalogs(out_dir=None, quiet=True, overwrite=False):
    """Download geospatial data catalogs from https://github.com/giswqs/geospatial-data-catalogs.

    Args:
        out_dir (str, optional): The output directory. Defaults to None.
        quiet (bool, optional): Whether to suppress the download progress bar. Defaults to True.
        overwrite (bool, optional): Whether to overwrite the existing data catalog. Defaults to False.

    Returns:
        str: The path to the downloaded data catalog.
    """
    import tempfile
    import gdown
    import zipfile

    if out_dir is None:
        out_dir = tempfile.gettempdir()
    elif not os.path.exists(out_dir):
        os.makedirs(out_dir)

    url = "https://github.com/giswqs/geospatial-data-catalogs/archive/refs/heads/master.zip"

    out_file = os.path.join(out_dir, "geospatial-data-catalogs.zip")
    work_dir = os.path.join(out_dir, "geospatial-data-catalogs-master")

    if os.path.exists(work_dir) and not overwrite:
        return work_dir
    else:

        gdown.download(url, out_file, quiet=quiet)
        with zipfile.ZipFile(out_file, "r") as zip_ref:
            zip_ref.extractall(out_dir)
        return work_dir


def set_default_bands(bands):

    excluded = [
        "index",
        "metadata",
        "mtl.json",
        "mtl.txt",
        "mtl.xml",
        "qa",
        "qa-browse",
        "QA",
        "rendered_preview",
        "tilejson",
        "tir-browse",
        "vnir-browse",
        "xml",
    ]

    for band in excluded:
        if band in bands:
            bands.remove(band)

    if len(bands) == 0:
        return [None, None, None]

    if isinstance(bands, str):
        bands = [bands]

    if not isinstance(bands, list):
        raise ValueError("bands must be a list or a string.")

    if set(["nir", "red", "green"]) <= set(bands):
        return ["nir", "red", "green"]
    elif set(["nir08", "red", "green"]) <= set(bands):
        return ["nir08", "red", "green"]
    elif set(["red", "green", "blue"]) <= set(bands):
        return ["red", "green", "blue"]
    elif set(["B8", "B4", "B3"]) <= set(bands):
        return ["B8", "B4", "B3"]
    elif set(["B4", "B3", "B2"]) <= set(bands):
        return ["B4", "B3", "B2"]
    elif set(["B3", "B2", "B1"]) <= set(bands):
        return ["B3", "B2", "B1"]
    elif set(["B08", "B04", "B03"]) <= set(bands):
        return ["B08", "B04", "B03"]
    elif set(["B04", "B03", "B02"]) <= set(bands):
        return ["B04", "B03", "B02"]
    elif len(bands) < 3:
        return [bands[0]] * 3
    else:
        return bands[:3]