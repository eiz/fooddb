# FoodData Central Database Dictionary

This document provides a comprehensive overview of the USDA FoodData Central database structure as used in FoodDB.

## Overview

FoodData Central (FDC) is a USDA database that provides expanded nutrient profile data and links to related agricultural and experimental research. The FoodDB application uses this data to provide a searchable database of food and nutrition information.

## Database Tables

### Core Food Tables

#### Food

The central entity that represents any substance consumed by humans for nutrition, taste, and/or aroma.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | Unique permanent identifier of the food (Primary Key) |
| data_type | String | Type of food data (e.g., Foundation, SR Legacy, Survey, Branded) |
| description | String | Description of the food |
| food_category_id | String | ID of the food category the food belongs to |
| publication_date | Date | Date when the food was published to FoodData Central |
| scientific_name | String | The scientific name for the food |

### Food Type Tables

#### Foundation Food

Foods whose nutrient and food component values are derived primarily by chemical analysis with extensive metadata.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |
| NDB_number | String | Unique number assigned for the food, different from fdc_id |
| footnote | String | Comments on any unusual aspects of the food |

#### SR Legacy Food

Foods from the April 2018 release of the USDA National Nutrient Database for Standard Reference.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |
| NDB_number | String | Unique number assigned for final food, starts from 100,000 |

#### Survey FNDDS Food

Foods whose consumption is measured by the What We Eat In America dietary survey component of NHANES.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |
| food_code | String | A unique ID identifying the food within FNDDS |
| wweia_category_number | Integer | ID for WWEIA food category to which this food is assigned |
| start_date | Date | Start date indicates time period corresponding to WWEIA data |
| end_date | Date | End date indicates time period corresponding to WWEIA data |

#### Branded Food

Foods whose nutrient values are typically obtained from food label data provided by food brand owners.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table (Primary Key) |
| brand_owner | String | Brand owner for the food |
| brand_name | String | Brand name for the food |
| subbrand_name | String | Subbrand and variation descriptions |
| gtin_upc | String | GTIN or UPC code identifying the food |
| ingredients | Text | List of ingredients (as it appears on the product label) |
| not_a_significant_source_of | String | Full text for the "not a significant source of…" label claim |
| serving_size | Float | Amount of the serving size when expressed as gram or ml |
| serving_size_unit | String | Unit used to express the serving size (gram or ml) |
| household_serving_fulltext | String | Amount and unit of serving size when expressed in household units |
| branded_food_category | String | Category of the branded food, assigned by GDSN or Label Insight |
| data_source | String | Source of the data (GDSN or Label Insight) |
| package_weight | String | Weight of the package |
| modified_date | Date | Date when the product data was last modified by the manufacturer |
| available_date | Date | Date when the product was available for inclusion in the database |
| market_country | String | The primary country where the product is marketed |
| discontinued_date | Date | Date when the product was discontinued |
| preparation_state_code | String | Code to describe the preparation of the food |
| trade_channel | String | Locations or programs in which the food is available |
| short_description | String | Manufacturer's short description of the product |
| material_code | String | The material code for the food, if present |

#### Agricultural Samples

Non-processed foods obtained directly from the location where they are produced.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |
| acquisition_date | Date | The date this food was obtained |
| market_class | String | The specific kind of this food (e.g., "Pinto" for pinto beans) |
| treatment | String | Special condition relevant to production (e.g., "drought" or "control") |
| state | String | The state in which this food was produced |

#### Sample Food

A food that is acquired as a representative sample of the food supply.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |

#### Sub Sample Food

A portion of a sample food used for specific chemical analysis.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |
| fdc_id_of_sample_food | Integer | ID of the sample food from which the sub sample originated |

### Nutrient Tables

#### Nutrient

Represents nutritional components found in foods.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier (Primary Key) |
| name | String | Name of the nutrient |
| unit_name | String | Unit used to express the nutrient amount (e.g., g, mg, μg) |
| nutrient_nbr | String | Nutrient number |
| rank | Float | Relative importance of the nutrient |

#### Food Nutrient

Links foods to their nutrient values.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier (Primary Key) |
| fdc_id | Integer | ID of the food this nutrient value pertains to |
| nutrient_id | Integer | ID of the nutrient to which this value pertains |
| amount | Float | Amount of the nutrient per 100g of food |
| data_points | Integer | Number of observations on which the value is based |
| derivation_id | Integer | ID of the derivation method used to derive the value |
| min | Float | The minimum amount |
| max | Float | The maximum amount |
| median | Float | The median amount |
| loq | Float | Limit of quantification as provided by laboratory |
| footnote | String | Comments on any unusual aspects of the food nutrient |
| min_year_acquired | Integer | Minimum purchase year of all acquisitions used to derive the value |

#### Food Nutrient Derivation

Procedure indicating how a food nutrient value was obtained.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| code | String | Code used for the derivation (e.g., A means analytical) |
| description | String | Description of the derivation |

#### Food Nutrient Source

An information source from which food nutrient values can be obtained.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| code | String | Code used for the source (e.g., 4 means calculated or imputed) |
| description | String | Description of the source |

#### FNDDS Derivation

Table for FNDDS nutrient derivation information.

| Field | Type | Description |
|-------|------|-------------|
| derivation_code | String | Derivation code as defined by FDC |
| derivation_description | String | The description of the derivation code |
| sr_addmod_year | Integer | Year value added or last modified as defined by SR |
| foundation_year_acquired | Integer | Initial year acquired as defined by FDC |
| start_date | Date | Start date of FNDDS version released |
| end_date | Date | End date of FNDDS version released |

#### FNDDS Ingredient Nutrient Value

Nutrient values for FNDDS ingredients.

| Field | Type | Description |
|-------|------|-------------|
| ingredient_code | String | Identifies only NDB number |
| ingredient_description | String | Description of NDB number |
| nutrient_code | String | 3-digit identification number |
| nutrient_value | Float | Amount per 100g edible portion for energy and nutrients |
| nutrient_value_source | String | FDC or other source for nutrient value |
| fdc_id | Integer | Identifier of food in FDC |
| derivation_code | String | Derivation code as defined by FDC |

### Food Component and Structure Tables

#### Food Component

A constituent part of a food (e.g., bone is a component of meat).

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier (Primary Key) |
| fdc_id | Integer | ID of the food this component pertains to |
| name | String | The kind of component (e.g., bone) |
| pct_weight | Float | Weight of the component as a percentage of the total food weight |
| is_refuse | Boolean | Whether the component is refuse (not edible) |
| gram_weight | Float | Weight of the component in grams |
| data_points | Integer | Number of observations on which the measure is based |
| min_year_acquired | Integer | Minimum purchase year of all acquisitions used to derive the value |

#### Food Portion

Represents discrete amounts of food and their weight equivalents.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier (Primary Key) |
| fdc_id | Integer | ID of the food this portion pertains to |
| seq_num | Integer | Display order for the measure |
| amount | Float | Number of measure units (e.g., if measure is 3 tsp, the amount is 3) |
| measure_unit_id | String | Unit used for the measure (e.g., tsp, cup) |
| portion_description | String | Description of the portion |
| modifier | String | Qualifier of the measure (e.g., melted, crushed, diced) |
| gram_weight | Float | Weight of the measure in grams |
| data_points | Integer | Number of observations on which the measure is based |
| footnote | String | Comments on any unusual aspects of the measure |
| min_year_acquired | Integer | Minimum purchase year of all acquisitions used to derive the value |

#### Input Food

A food that is an ingredient or a source food to another food.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier (Primary Key) |
| fdc_id | Integer | ID of the food that contains the input food |
| fdc_id_of_input_food | Integer | ID of the food that is the input food |
| seq_num | Integer | Order in which to display the input food |
| amount | Float | Amount of the input food included (in terms of unit) |
| sr_code | String | The FF/SR code of the ingredient food |
| sr_description | String | Description of the ingredient food |
| unit | String | Unit of measure for the amount of the input food |
| portion_code | String | Code that identifies the portion description |
| portion_description | String | Description of the portion used to measure the amount |
| gram_weight | Float | Weight in grams of the input food |
| retention_code | String | Code identifying processing that may have impacted nutrient content |

### Conversion and Calculation Tables

#### Food Calorie Conversion Factor

Multiplication factors for calculating energy from macronutrients for a specific food.

| Field | Type | Description |
|-------|------|-------------|
| food_nutrient_conversion_factor_id | Integer | ID of the related row in the nutrient_conversion_factor table |
| protein_value | Float | The multiplication factor for protein |
| fat_value | Float | The multiplication factor for fat |
| carbohydrate_value | Float | The multiplication factor for carbohydrates |

#### Food Protein Conversion Factor

Factors used to calculate protein from nitrogen.

| Field | Type | Description |
|-------|------|-------------|
| food_nutrient_conversion_factor_id | Integer | ID of the related row in the nutrient_conversion_factor table |
| value | Float | The multiplication factor used to calculate protein from nitrogen |

#### Food Nutrient Conversion Factor

Top level type for all types of nutrient conversion factors.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| fdc_id | Integer | ID of the food this conversion factor pertains to |

### Metadata and Reference Tables

#### Food Category

Foods of defined similarity.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| code | String | Food group code |
| description | String | Description of the food group |

#### Food Attribute

The value for a generic property of a food.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| fdc_id | Integer | ID of the food this attribute pertains to |
| seq_num | Integer | The order the attribute will be displayed on the released food |
| food_attribute_type_id | Integer | ID of the type of food attribute this value is associated with |
| name | String | Name of food attribute |
| value | String | The actual value of the attribute |

#### Food Attribute Type

The list of supported attributes associated with a food.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| name | String | Name of the attribute - should be displayable to users |
| description | String | Description of the attribute |

#### Food Update Log Entry

Historical record of an update of food data.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id | Integer | ID of the food in the food table |
| description | String | Description of the food |
| fdc_publication_date | Date | Date when the food was published to FoodData Central |

#### Lab Method

A chemical procedure used to measure the amount of one or more nutrients in a food.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| description | String | Description of the lab method |
| technique | String | General chemical analysis approach used by the lab method |

#### Lab Method Code

A short sequence of characters used to identify a lab method.

| Field | Type | Description |
|-------|------|-------------|
| lab_method_id | Integer | ID of the lab method the code refers to |
| code | String | Value of the method code |

#### Lab Method Nutrient

A nutrient whose amount can be measured by a lab method.

| Field | Type | Description |
|-------|------|-------------|
| lab_method_id | Integer | ID of the lab method the nutrient is measured by |
| nutrient_id | Integer | ID of the nutrient that can be measured by the method |

#### Retention Factor

Factors used to calculate nutrient retention after cooking.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique permanent identifier |
| retention_code | String | Code for the retention factor |
| food_group_code | String | Food group code |
| retention_description | String | Description of the retention factor |

#### Sub Sample Result

The result of chemical analysis of a lab on a particular sub sample for a nutrient.

| Field | Type | Description |
|-------|------|-------------|
| food_nutrient_id | Integer | Unique ID for row, same as the food_nutrient ID |
| adjusted_amount | Float | Amount after adjusting for unit |
| lab_method_id | Integer | ID of the lab method used to measure the nutrient |
| nutrient_name | String | The name of the nutrient as supplied by the lab |

#### Acquisition Samples

Links between acquisitions and sample foods.

| Field | Type | Description |
|-------|------|-------------|
| fdc_id_of_sample_food | Integer | ID of the sample food that uses the acquisitioned food |
| fdc_id_of_acquisition_food | Integer | ID of the acquisitioned food used in the sample food |

#### WWEIA Food Category

Food categories for FNDDS.

| Field | Type | Description |
|-------|------|-------------|
| wweia_food_category_code | Integer | Unique identification code |
| wweia_food_category_description | String | Description for a WWEIA Category |

## Data Types

FoodData Central contains these main types of food data:

1. **Foundation Foods**: Foods with nutrient values derived primarily by chemical analysis. Include extensive metadata about samples, locations, dates, and analytical methods.

2. **SR Legacy Foods**: Foods from the USDA National Nutrient Database for Standard Reference, with nutrient values derived from analysis and calculation.

3. **Survey (FNDDS) Foods**: Foods measured in the What We Eat In America dietary survey. Nutrient values are usually calculated from Branded and SR Legacy data.

4. **Branded Foods**: Foods with nutrient values from food label data provided by food brand owners.

5. **Agricultural/Sample Foods**: Non-processed foods obtained directly from the location where they are produced, used as samples for analysis.

## Data Relationships

- Each **Food** can have multiple **FoodNutrients**, linking it to specific nutrients with their amounts.
- Different food types (**Foundation**, **SR Legacy**, **Survey**, **Branded**) are specialized classifications of the base **Food** entity.
- **FoodComponents** represent constituent parts of a **Food**, such as edible and non-edible portions.
- **FoodPortions** define different serving sizes and their gram equivalents for a food.
- **InputFoods** represent ingredients or source foods that make up a composite **Food**.
- **Lab Methods** and their results provide metadata about how nutrient values were determined.
- **Conversion Factors** are used to calculate energy values and other derived nutrient information.

## Data Import Process

The database is populated from CSV files provided by the USDA FoodData Central system. The import process includes:

1. Reading CSV files using pandas
2. Data cleaning and validation
3. Parsing dates and numeric values
4. Bulk insertion into SQLite database
5. Creating indexes for query performance
6. Generating embeddings for search functionality

## Additional Resources

- [USDA FoodData Central](https://fdc.nal.usda.gov/)
- [FoodData Central API Documentation](https://fdc.nal.usda.gov/api-guide.html)