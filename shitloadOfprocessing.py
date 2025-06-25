"""
This is legacy from Tool Extract Hierarchy.

There was a ton of post processing that was added to the data.
I have to check if it is useful. For now, I leave it here.

"""


def post_processing(df_hierarchy):

    # re order the columns to get level1,... first following by name,id,type
    df_hierarchy = df_hierarchy[[c for c in df_hierarchy if c not in [
        'name', '_id', 'type']] + ['name', '_id', 'type']]
    df_hierarchy = df_hierarchy[df_hierarchy['level1']
        != 'Recycle bin'].reset_index(drop=True)


    #-----------------------------------------------------------------------------Factory name---------------------------------------------------------------------------

    try : 
        df_factory = df_hierarchy[df_hierarchy['type'] == 16777221]
        # Get the factory ID list
        factory_id_list = df_factory['_id'].unique().tolist()

        # Use set intersection directly in get_factory_id()
        def get_factory_id(path):
            return list(set(factory_id_list).intersection(path))
        
        # Apply the get_factory_id() function to each row in the 'paths' column of df_hierarchy
        df_hierarchy['Factory_id'] = df_hierarchy['paths'].apply(get_factory_id)

        # Define a function that takes a list as input and returns the last element as a string, or 'noid' if the list is empty
        def get_string_from_list(list_elem):
            return str(max(list_elem, default='noid'))
        
        # Apply the get_string_from_list() function to the 'Factory_id' column of df_hierarchy
        # This converts each list of factory IDs to a string containing the last (most specific) ID in the list
        df_hierarchy['Factory_id'] = df_hierarchy['Factory_id'].apply(lambda x: get_string_from_list(x))

        # Extract the columns 'name' and '_id' from df_factory, and rename them to 'factory_name' and 'Factory_id', respectively
        df_factory = df_factory[['name', '_id']].rename(columns={'name': 'factory_name', '_id': 'Factory_id'})
        print("factory ",len(df_factory))

        # Merge df_hierarchy with df_factory on the 'Factory_id' column, using a left join to preserve all rows in df_hierarchy
        # This adds the 'factory_name' column to df_hierarchy, which contains the name of the factory corresponding to each row
        df_hierarchy_with_plant_name = pd.merge(df_hierarchy, df_factory, on='Factory_id', how='left') 
    except Exception as e :
        print('no factory extracted ', e)
        df_hierarchy_with_plant_name = df_hierarchy
        df_hierarchy_with_plant_name['Factory_id'] = 'nullFid'
        df_hierarchy_with_plant_name['factory_Name'] = 'nullFn'


    #--------------------------------------------------------------------------ASset name / asset Id ------------------------------------------------------------------

    try :

        df_asset = df_hierarchy[df_hierarchy['type'] == 33554432]
        # Get the asset ID list
        asset_id_list = df_asset['_id'].unique().tolist()

        # Use set intersection directly in get_asset_id()
        def get_asset_id(path):
            return list(set(asset_id_list).intersection(path))
        
        # Apply the get_asset_id() function to each row in the 'paths' column of df_hierarchy
        df_hierarchy_with_plant_name['Asset_id'] = df_hierarchy['paths'].apply(get_asset_id)
        
        # Apply the get_string_from_list() function to the 'Asset_id' column of df_hierarchy
        # This converts each list of asset IDs to a string containing the last (most specific) ID in the list
        df_hierarchy_with_plant_name['Asset_id'] = df_hierarchy_with_plant_name['Asset_id'].apply(lambda x: get_string_from_list(x))

        # Extract the columns 'name' and '_id' from df_asset, and rename them to 'asset_name' and 'Asset_id', respectively
        df_asset = df_asset[['name', '_id']].rename(columns={'name': 'asset_name', '_id': 'Asset_id'})
        print("asset ",len(df_asset))

        # Merge df_hierarchy with df_asset on the 'Asset_id' column, using a left join to preserve all rows in df_hierarchy
        # This adds the 'asset_name' column to df_hierarchy, which contains the name of the asset corresponding to each row
        df_hierarchy_with_plant_name_with_asset_name = pd.merge(df_hierarchy_with_plant_name, df_asset, on='Asset_id', how='left')

    except Exception as e :
        print('no asset extracted ', e)
        df_hierarchy_with_plant_name_with_asset_name = df_hierarchy_with_plant_name
        df_hierarchy_with_plant_name_with_asset_name['Asset_id'] = 'null_Aid'
        df_hierarchy_with_plant_name_with_asset_name['asset_name'] = 'nullAn'

#--------------------------------------------------------------------------Zone and zone id ------------------------------------------------------------------
    try :

        df_zone = df_hierarchy[df_hierarchy['type'] == 16777222]

        # Get the zone ID list
        zone_id_list = df_zone['_id'].unique().tolist()

        # Use set intersection directly in get_zone_id()
        def get_zone_id(path):
            return list(set(zone_id_list).intersection(path))

        # Apply the get_zone_id() function to each row in the 'paths' column of df_hierarchy
        df_hierarchy_with_plant_name_with_asset_name['Zone_id'] = df_hierarchy['paths'].apply(get_zone_id)

        # Define a function that takes a list as input and returns the last element as a string, or 'noid' if the list is empty
        #def get_string_from_list(list_elem):
        #    return str(max(list_elem, default='noid'))
        
        # Apply the get_string_from_list() function to the 'Zone_id' column of df_hierarchy
        # This converts each list of zone IDs to a string containing the last (most specific) ID in the list
        df_hierarchy_with_plant_name_with_asset_name['Zone_id'] = df_hierarchy_with_plant_name_with_asset_name['Zone_id'].apply(lambda x: get_string_from_list(x))

        # Extract the columns 'name' and '_id' from df_zone, and rename them to 'zone_name' and 'Zone_id', respectively
        df_zone = df_zone[['name', '_id']].rename(columns={'name': 'zone_name', '_id': 'Zone_id'})
        print("zone ",len(df_zone))


        # Merge df_hierarchy with df_zone on the 'Zone_id' column, using a left join to preserve all rows in df_hierarchy
        # This adds the 'zone_name' column to df_hierarchy, which contains the name of the zone corresponding to each row
        df_hierarchy_with_plant_name_with_asset_name_with_zone = pd.merge(df_hierarchy_with_plant_name_with_asset_name, df_zone, on='Zone_id', how='left')

    except Exception as e :
            print("No zone extract")
            df_hierarchy_with_plant_name_with_asset_name_with_zone = df_hierarchy_with_plant_name_with_asset_name
            df_hierarchy_with_plant_name_with_asset_name_with_zone['Zone_id'] = 'nullZid'
            df_hierarchy_with_plant_name_with_asset_name_with_zone['zone_name'] = 'nullZn'



    return df_hierarchy_with_plant_name_with_asset_name_with_zone

    