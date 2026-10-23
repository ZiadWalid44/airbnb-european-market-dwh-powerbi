import urllib.parse
import pandas as pd
from sqlalchemy import create_engine

# 1. قراءة ملف الإكسيل المنظف (Silver Layer)
file_path = 'silver_airbnb_data.xlsx'
df = pd.read_excel(file_path)

# 2. بناء بيانات جدول المدن (dim_city) مع تسمية city_sk
dim_city = pd.DataFrame({'city_name': df['city'].unique()}).reset_index()
dim_city.rename(columns={'index': 'city_sk'}, inplace=True)
dim_city['city_sk'] += 1

# 3. بناء بيانات جدول العقار (dim_property) مع تسمية property_sk
dim_property = (
    df[['property_type', 'room_type', 'person_capacity', 'bedrooms']]
    .drop_duplicates()
    .reset_index(drop=True)
)
dim_property['property_sk'] = dim_property.index + 1

# 4. بناء بيانات جدول المرافق (dim_amenities) مع تسمية amenity_sk
dim_amenities = (
    df[['has_wifi', 'has_kitchen', 'has_ac']]
    .drop_duplicates()
    .reset_index(drop=True)
)
dim_amenities['amenity_sk'] = dim_amenities.index + 1

# 5. دمج المفاتيح البديلة (_sk) داخل جدول الحقائق (fact_listings)
fact_listings = df.merge(
    dim_city, left_on='city', right_on='city_name', how='left'
)
fact_listings = fact_listings.merge(
    dim_property,
    on=['property_type', 'room_type', 'person_capacity', 'bedrooms'],
    how='left',
)
fact_listings = fact_listings.merge(
    dim_amenities, on=['has_wifi', 'has_kitchen', 'has_ac'], how='left'
)

# اختيار وترتيب الأعمدة ليطابق أعمدة الجدول في SQL تماماً
# (لاحظ عدم تضمين listing_sk لأنه Identity يزيد تلقائياً في SQL Server)
fact_listings = fact_listings[[
    'Id',
    'city_sk',
    'property_sk',
    'amenity_sk',
    'realSum',
    'guest_satisfaction_overall',
    'cleanliness_rating',
    'number_of_reviews',
    'host_is_superhost',
    'lat',
    'lng',
]].rename(columns={'Id': 'listing_id_bk', 'realSum': 'price'})

# تحويل الأعمدة المنطقية إلى أرقام صحيحة لضمان توافقها التام مع نوع BIT في SQL
dim_amenities['has_wifi'] = dim_amenities['has_wifi'].astype(int)
dim_amenities['has_kitchen'] = dim_amenities['has_kitchen'].astype(int)
dim_amenities['has_ac'] = dim_amenities['has_ac'].astype(int)
fact_listings['host_is_superhost'] = fact_listings['host_is_superhost'].astype(int)

# 6. إعداد الاتصال بسيرفر SQL Server
# يمكنك استخدام '.' للنسخة الافتراضية MSSQLSERVER
server_name = r'localhost\MSSQLSERVER01'
database_name = 'Airbnb_DWH'

conn_str = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={server_name};'
    f'DATABASE={database_name};'
    f'Trusted_Connection=yes;'
    f'TrustServerCertificate=yes;'
)
quoted_conn_str = urllib.parse.quote_plus(conn_str)
engine = create_engine(f'mssql+pyodbc:///?odbc_connect={quoted_conn_str}')

# 7. تصدير الجداول بالترتيب المنطقي (جداول الأبعاد أولاً ثم جدول الحقائق)
print('جاري رفع جدول dim_city...')
dim_city.to_sql('dim_city', engine, if_exists='append', index=False)

print('جاري رفع جدول dim_property...')
dim_property.to_sql('dim_property', engine, if_exists='append', index=False)

print('جاري رفع جدول dim_amenities...')
dim_amenities.to_sql('dim_amenities', engine, if_exists='append', index=False)

print('جاري رفع جدول fact_listings...')
fact_listings.to_sql('fact_listings', engine, if_exists='append', index=False)

print('تم رفع جميع الجداول وتعبئة مستودع البيانات (Airbnb_DWH) بنجاح!')