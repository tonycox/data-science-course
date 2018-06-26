from sklearn.base import BaseEstimator
from sklearn.preprocessing import FunctionTransformer
from sklearn.pipeline import make_pipeline
import geocoder
import pandas as pd
import geopy.distance
import numpy as np
import time


def fill_none(df, def_value=0, columns=['building', 'municipality']):
    df = df.fillna(dict((el, def_value) for el in columns))
    return df


def columns_as_int(df, columns=['is_public', 'building', 'municipality', 'district', 'reason']):
    for column in columns:
        df[[column]] = np.nan_to_num(df[[column]])
        df[[column]] = df[[column]].astype(int)
    return df


def geocode_addres(df, address_column='address'):
    def geocode(row):
        addr = row[address_column]
        if addr and addr == addr:
            time.sleep(1.5)
            g = geocoder.yandex(addr)
            res = g.json
            if res:
                return g.json[address_column]
            else:
                return addr
        else:
            return addr

    df[address_column] = df.apply(geocode, axis=1)

    return df


def join_build_info(df, address_column='address', building_info=None):
    result = pd.merge(df,building_info,on=[address_column])
    return result

def label_encoder(df, columns=['status']):  # columns=['status', 'type_street']
    for c in columns:
        df[c] = df[c].astype('category')
    df[columns] = df[columns].apply(lambda x: x.cat.codes)
    return df


def drop_columns(df, columns=['type_of', 'url']):
    df.drop(columns, axis=1, inplace=True)
    return df

def delete_rows(df,column,value):
    res = df[df[column]!=value]
    return res


def search_near_shops(df,shops_info=None, thread_count = 10):
    from multiprocessing.dummy import Pool as ThreadPool
    coords = shops_info.as_matrix(columns=['lat', 'lon'])

    ids=df.index.values
    step=len(ids)//thread_count+1
    parts_df=[]
    for i in range(thread_count):
        start=step*i
        parts_df.append(df.loc[ids[start:start + step]])

    def op(df_part):
        df_part['count_nar_shops']=df_part.apply(lambda row: count_near_points((row['latitude'], row['longitude']), coords), axis=1)
        return df_part

    pool = ThreadPool(thread_count)
    results = pool.map(op, parts_df)
    pool.close()
    pool.join()

    result_df = pd.DataFrame(columns=df.columns.values)
    for part in results:
        result_df= result_df.append(part)

    return result_df
    # df['count_nar_shops']=df.apply(lambda row: count_near_points((row['latitude'],row['longitude']),coords),axis=1)


def count_near_points(origin, coort_matrix):
    import geopy.distance
    res = 0
    for cord in coort_matrix:
        dist = geopy.distance.vincenty(origin, cord).km
        if dist<=1:
            res+=1
    return res


# if __name__ == '__main__':
#     problems = pd.DataFrame.from_csv('../../data/workshop_1/csv/problems.csv')
#     df=problems.sample(n=int(len(problems)*.01), replace=True, random_state=42)
#     df=df.append(problems[problems['status']=='Не удовлетворён'])

#     shops = pd.read_csv('../../data/workshop_1/csv/shops.csv', encoding="UTF-8")

#     pipeline = make_pipeline(
#         FunctionTransformer(delete_rows, kw_args=dict(column='type_of',value='point'),validate=False),
#         # FunctionTransformer(fill_none, validate=False),
#         # FunctionTransformer(columns_as_int, validate=False),
#         # FunctionTransformer(geocode_addres, validate=False),
#         FunctionTransformer(search_near_shops, kw_args=dict(shops_info=shops), validate=False),
#         # FunctionTransformer(join_build_info,
#         #                      kw_args=dict(building_info_path='../../data/workshop_1/csv/buildings_info_transform.csv'),
#         #                     validate=False),
#         # FunctionTransformer(generate_new_features, validate=False),
#         # FunctionTransformer(label_encoder, validate=False),
#         # FunctionTransformer(drop_columns, kw_args=dict(columns=['type_of', 'url']), validate=False)
#     )
#     result = pipeline.transform(df)
#     # result.to_csv('../../data/workshop_1/csv/25_problems_geo.csv',index=True,encoding='utf-8')
#     print(result)
