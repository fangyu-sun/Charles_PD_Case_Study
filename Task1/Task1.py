import pandas as pd
import numpy as np
from datetime import datetime
import pyreadstat
import re
import os


def clean_and_format_data(df):
    """
    Main function for data cleaning and format conversion
    """
    #  Create a copy of the dataset
    df_clean = df.copy()

    # 1. Remove rows with logical errors or missing key data
    df_clean = remove_invalid_cases(df_clean)

    # 2. Process multi-response questions (one-hot encoding)
    df_clean = process_multiresponse_questions(df_clean)

    # 3. Convert text labels to numeric codes
    df_clean = convert_labels_to_codes(df_clean)

    # 4. Rename columns and reorder them according to questionnaire structure
    df_clean = rename_and_reorder_columns(df_clean)

    # 5. Create 'Wave' variable (weekly grouping)
    df_clean = create_wave_variable(df_clean)

    # 6. Define variable labels and value labels for SPSS export
    variable_labels, value_labels = create_labels()

    return df_clean, variable_labels, value_labels


def remove_invalid_cases(df):
    """
    Remove invalid records – delete those with logic errors and missing data
    """

    # Record original row count
    original_count = len(df)

    # Remove completely blank rows
    df = df.dropna(how='all').reset_index(drop=True)

    # Handle spaces and empty strings: convert whitespace-only values to NaN
    df = df.replace(r'^\s*$', np.nan, regex=True)

    # Key variables: Gender, Age, Postcode, CompletedDate
    key_columns = ['What is your gender?', 'What is your age?', 'What is your postcode?', 'CompletedDate']

    # Error1
    # Remove rows with missing key variables
    error1 = df[key_columns].isna().any(axis=1)
    print(f"Error1: Number of records with missing key variables: {error1.sum()}")
    df = df[~error1].reset_index(drop=True)
    
    # Display IDs of these records for inspection
    if error1.sum() > 0:
        error_ids = df.loc[error1, 'ID'].tolist()
        print(f"Error1 ID: {error_ids}")

    # Error2
    # Remove rows where age is "Under 18" (should terminate based on survey logic)
    error2 = df['What is your age?'] == 'Under 18'
    print(f"Error2: Number of records where age is under 18:{error2.sum()}")
    df = df[~error2].reset_index(drop=True)

    # Display IDs of these records for inspection
    if error2.sum() > 0:
        error_ids = df.loc[error2, 'ID'].tolist()
        print(f"Error2 ID: {error_ids}")

    # Error3: 
    # Select participants who chose Q1_99 "None of these" (SKIP to Q6).
    q1_none_selected = df['Which of the following brands of electricity providers are you aware of?'].str.contains(
        'None of these', na=False, regex=False)

    # For records selecting Q1_99 ("None of these"), remove Q2–Q5 data.
    q2_q5_columns = [
        'And which ONE of these brands is your main provider?',
        'Thinking about \'Origin\', how favourable is your overall impression of them?',
        'How likely are you to recommend \'Origin\' to friends or family?',
        'How would you rate \'Origin\' on each of the following? (Trustworthiness)',
        'How would you rate \'Origin\' on each of the following? (Value for money)',
        'How would you rate \'Origin\' on each of the following? (Customer service)',
        'How would you rate \'Origin\' on each of the following? (Innovation)'
    ]

    # Only keep the columns exist
    existing_q2_q5_columns = [col for col in q2_q5_columns if col in df.columns]

    # Check logic Error3: selected Q1_99, but answered Q2-Q5.
    if existing_q2_q5_columns:
        error3 = q1_none_selected & df[existing_q2_q5_columns].notna().any(axis=1)
        print(f"Error3: Number of selected Q1_99,but answered Q2-Q5: {error3.sum()}records")

        # Show Logic1 Error ID for checking to delete
        if error3.sum() > 0:
            error_ids = df.loc[error3, 'ID'].tolist()
            print(f"Error3 ID: {error_ids}")

        df = df.loc[~error3].reset_index(drop=True)

    # Error4
    # Check logic error4：Not Origin user,but answered Q3-Q5
    if 'And which ONE of these brands is your main provider?' in df.columns:
        origin_main_provider = df['And which ONE of these brands is your main provider?'] == 'Origin'

        # Check if Q3-Q5 have data
        q3_q5_columns = [
            'Thinking about \'Origin\', how favourable is your overall impression of them?',
            'How likely are you to recommend \'Origin\' to friends or family?',
            'How would you rate \'Origin\' on each of the following? (Trustworthiness)',
            'How would you rate \'Origin\' on each of the following? (Value for money)',
            'How would you rate \'Origin\' on each of the following? (Customer service)',
            'How would you rate \'Origin\' on each of the following? (Innovation)'
        ]

        # Only keep the existed actual column
        existing_q3_q5_columns = [col for col in q3_q5_columns if col in df.columns]

        if existing_q3_q5_columns:
            # Consider answered if any of Q3–Q5 columns contain data
            has_q3_q5_data = df[existing_q3_q5_columns].notna().any(axis=1)

            # Non-Origin users who answered Q3–Q5 and did not select Q1_99
            error4 = ~origin_main_provider & has_q3_q5_data & ~q1_none_selected
            print(f"Error4: Number of (non-Origin users answered Q3–Q5)records: {error4.sum()}records")
 
            # Display IDs of these records for inspection
            if error4.sum() > 0:
                error_ids = df.loc[error4, 'ID'].tolist()
                print(f"Error4 ID: {error_ids}")
            
            # Use .loc to avoid warnings
            df = df.loc[~error4].reset_index(drop=True)

    #Error5
    # Check logic error5：Q6 answered "No" or "Don't know" but also answered Q7    if 'In the past 12 months, have you seen or heard any advertising for \'Origin\'?' in df.columns:
    if 'In the past 12 months, have you seen or heard any advertising for \'Origin\'?' in df.columns:
        q6_no_advertising = df['In the past 12 months, have you seen or heard any advertising for \'Origin\'?'].isin(
            ['No', 'Don\'t know'])
        has_q7_data = df['Where did you see or hear advertising for \'Origin\'?'].notna()

        error5 = q6_no_advertising & has_q7_data
        print(f"Error5: Number of (Q6 answered \"No\" or \"Don't know\" but also answered Q7)records: {error5.sum()}records")
        # Use .loc to avoid warnings
        df = df.loc[~error5].reset_index(drop=True)

        # Display IDs of these records for inspection
        if error5.sum() > 0:
            error_ids = df.loc[error5, 'ID'].tolist()
            print(f"Error5 ID: {error_ids}")

    final_count = len(df)
    print(f"Invalid record removal completed: {original_count} -> {final_count}")

    return df


def create_multiresponse_columns(df, column, options, question_code):
    """
    Create one-hot encoded columns for multi-response questions
    """
    # Create new binary columns
    for label, code in options.items():
        new_col_name = f"{question_code}_{code}"

        if label == 'Other (please specify)':
            # "Others" option requires checking a separate column
            other_col = f"{column} (Other (please specify))"
            if other_col in df.columns:
                df[new_col_name] = df[other_col].notna().astype(int)
            else:
                df[new_col_name] = 0
        elif label == 'None of these':
            # Check if "None of these" is included (use regex for matching
            df[new_col_name] = df[column].str.contains(re.escape('None of these'), na=False).astype(int)
        else:
            # Check if the brand is included (use regex for matching)
            df[new_col_name] = df[column].str.contains(re.escape(label), na=False, regex=False).astype(int)

    return df


def process_multiresponse_questions(df):
    """
    Process one-hot encoding for multi-response questions
    """

    # Q1: Bradn Awarness
    q1_options = {
        'Synergy': '1',
        'Western Power': '2',
        'AGL': '3',
        'Origin': '4',
        'Horizon Power': '5',
        'Red Energy': '6',
        'Other (please specify)': '97',
        'None of these': '99'
    }

    # Process Q1 multi-response
    q1_col = 'Which of the following brands of electricity providers are you aware of?'
    df = create_multiresponse_columns(df, q1_col, q1_options, 'Q1')

    # Q7: Advertising channels
    q7_options = {
        'TV': '1',
        'Online / Social media': '2',
        'Outdoor (billboards, bus stops, etc.)': '3',
        'Radio': '4',
        'Print (newspaper, magazine)': '5',
        'Other (please specify)': '97'
    }

    # Process Q7 multi-response
    q7_col = 'Where did you see or hear advertising for \'Origin\'?'
    df = create_multiresponse_columns(df, q7_col, q7_options, 'Q7')

    return df


def convert_labels_to_codes(df):
    """
    Convert text labels to numeric codes
    """

    # S1: Gender
    gender_mapping = {
        'Male': 1,
        'Female': 2,
        'Non-binary / Other': 3,
        'Prefer not to say': 99
    }
    df['What is your gender?'] = df['What is your gender?'].map(gender_mapping)

    # S2: Age
    age_mapping = {
        '18-24': 2,
        '25-34': 3,
        '35-44': 4,
        '45-54': 5,
        '55-64': 6,
        '65+': 7
    }
    df['What is your age?'] = df['What is your age?'].map(age_mapping)

    # Q2: Main Supplier
    provider_mapping = {
        'Synergy': 1,
        'Western Power': 2,
        'AGL': 3,
        'Origin': 4,
        'Horizon Power': 5,
        'Red Energy': 6,
        'Other (please specify)': 97,
        'None of these': 99
    }
    df['And which ONE of these brands is your main provider?'] = df[
        'And which ONE of these brands is your main provider?'].map(provider_mapping)

    # Q3: Brand perception (only for Origin users)
    favourable_mapping = {
        'Very unfavourable': 1,
        'Somewhat unfavourable': 2,
        'Neutral': 3,
        'Somewhat favourable': 4,
        'Very favourable': 5
    }
    df['Thinking about \'Origin\', how favourable is your overall impression of them?'] = df[
        'Thinking about \'Origin\', how favourable is your overall impression of them?'].map(favourable_mapping)

    # Q4a: Likelihood to recommend
    def convert_recommendation(value):
        if pd.isna(value):
            return np.nan
        if 'Not at all likely' in str(value) or value == '0':
            return 0
        if 'Extremely likely' in str(value) or value == '10':
            return 10
        try:
            return int(float(value))
        except:
            return np.nan

    df['How likely are you to recommend \'Origin\' to friends or family?'] = df[
        'How likely are you to recommend \'Origin\' to friends or family?'].apply(convert_recommendation)

    # Q5: Attribute ratings
    rating_mapping = {
        'Very poor': 1,
        'Poor': 2,
        'Fair': 3,
        'Good': 4,
        'Excellent': 5,
        'Don\'t know': 98
    }

    rating_columns = [
        'How would you rate \'Origin\' on each of the following? (Trustworthiness)',
        'How would you rate \'Origin\' on each of the following? (Value for money)',
        'How would you rate \'Origin\' on each of the following? (Customer service)',
        'How would you rate \'Origin\' on each of the following? (Innovation)'
    ]

    for col in rating_columns:
        df[col] = df[col].map(rating_mapping)

    # Q6: Advertising exposure
    advertising_mapping = {
        'Yes': 1,
        'No': 2,
        'Don\'t know': 98
    }
    df['In the past 12 months, have you seen or heard any advertising for \'Origin\'?'] = df[
        'In the past 12 months, have you seen or heard any advertising for \'Origin\'?'].map(advertising_mapping)

    # D1: Work status
    work_mapping = {
        'Working full time': 1,
        'Working part time': 2,
        'Self-employed': 3,
        'Student': 4,
        'Unemployed and looking for work': 5,
        'Retired': 6,
        'Other (please specify)': 97
    }
    df['Which of the following best describes your current work status?'] = df[
        'Which of the following best describes your current work status?'].map(work_mapping)

    # D2: Income
    income_mapping = {
        'Less than $30,000': 1,
        '$30,000-$59,999': 2,
        '$60,000–$89,999': 3,
        '$90,000–$119,999': 4,
        '$120,000–$149,999': 5,
        '$150,000 or more': 6,
        'Prefer not to say': 99
    }
    df['Which of the following best describes your total annual household income?'] = df[
        'Which of the following best describes your total annual household income?'].map(income_mapping)

    # D3: Household structure
    household_mapping = {
        'Live alone': 1,
        'Single, no children': 2,
        'Single parent with children at home': 3,
        'Couple, no children': 4,
        'Couple, with children at home': 5,
        'Group household / share house': 6,
        'Other (please specify)': 97
    }
    df['Which of the following best describes your household structure?'] = df[
        'Which of the following best describes your household structure?'].map(household_mapping)

    return df


def rename_and_reorder_columns(df):
    """
    Rename columns and adjust their order
    """

    # Rename columns
    column_mapping = {
        'ID': 'ID',
        'What is your gender?': 'S1',
        'What is your age?': 'S2',
        'What is your postcode?': 'S3',
        'And which ONE of these brands is your main provider?': 'Q2',
        'And which ONE of these brands is your main provider? (Other (please specify))': 'Q2_97_Oth',
        'Thinking about \'Origin\', how favourable is your overall impression of them?': 'Q3',
        'How likely are you to recommend \'Origin\' to friends or family?': 'Q4a',
        'You said you would be [unlikely/likely] to recommend \'Origin\'. Why do you say that?': 'Q4b',
        'How would you rate \'Origin\' on each of the following? (Trustworthiness)': 'Q5_1',
        'How would you rate \'Origin\' on each of the following? (Value for money)': 'Q5_2',
        'How would you rate \'Origin\' on each of the following? (Customer service)': 'Q5_3',
        'How would you rate \'Origin\' on each of the following? (Innovation)': 'Q5_4',
        'In the past 12 months, have you seen or heard any advertising for \'Origin\'?': 'Q6',
        'Where did you see or hear advertising for \'Origin\'? (Other (please specify))': 'Q7_97_Oth',
        'Which of the following best describes your current work status?': 'D1',
        'Which of the following best describes your current work status? (Other (please specify))': 'D1_97_Oth',
        'Which of the following best describes your total annual household income?': 'D2',
        'Which of the following best describes your household structure?': 'D3',
        'Which of the following best describes your household structure? (Other (please specify))': 'D3_97_Oth',
        'CompletedDate': 'CompletedDate'
    }

    # Add special mapping for Q1_97_Oth
    q1_other_col = 'Which of the following brands of electricity providers are you aware of? (Other (please specify))'
    if q1_other_col in df.columns:
        column_mapping[q1_other_col] = 'Q1_97_Oth'

    # Apply renaming
    df = df.rename(columns=column_mapping)

    # Define column order
    column_order = [
        'ID', 'S1', 'S2', 'S3',
        # Q1 multi-response columns
        'Q1_1', 'Q1_2', 'Q1_3', 'Q1_4', 'Q1_5', 'Q1_6', 'Q1_99', 'Q1_97', 'Q1_97_Oth',
        # Q2
        'Q2', 'Q2_97_Oth',
        # Q3-Q5
        'Q3', 'Q4a', 'Q4b', 'Q5_1', 'Q5_2', 'Q5_3', 'Q5_4',
        # Q6
        'Q6',
        # Q7 multi-response columns
        'Q7_1', 'Q7_2', 'Q7_3', 'Q7_4', 'Q7_5', 'Q7_97', 'Q7_97_Oth',
        # Demographics
        'D1', 'D1_97_Oth', 'D2', 'D3', 'D3_97_Oth',
        # Wave and Completed date
        'Wave', 'CompletedDate'
    ]

    # Ensure all columns exist
    existing_columns = [col for col in column_order if col in df.columns]
    extra_columns = [col for col in df.columns if col not in column_order]

    # Reorder columns
    df = df[existing_columns + extra_columns]

    # Remove original multi-response columns（one-hot already existed）
    columns_to_drop = [
        'Which of the following brands of electricity providers are you aware of?',
        'Where did you see or hear advertising for \'Origin\'?'
    ]

    # Drop only main columns, keep other specified ones
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    return df


def create_wave_variable(df):
    """
    Create Wave variable and categorize by week
    """

    # Convert date format
    df['CompletedDate'] = pd.to_datetime(df['CompletedDate'])

    # Calculate weekly grouping (Mon–Sun)
    def get_week_number(date):
        # Find the most recent Monday (e.g., 4 Aug)
        start_date = datetime(2025, 8, 4)  
        delta = (date - start_date).days
        week_num = (delta // 7) + 1
        return max(1, week_num)  # Ensure at least 1

    df['Wave'] = df['CompletedDate'].apply(get_week_number)

    # Convert CompletedDate back to string to preserve original format
    df['CompletedDate'] = df['CompletedDate'].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df


def create_labels():
    """
    Create variable labels and value labels
    """

    # Simple Question texts
    question_texts = {
        'S1': 'What is your gender?',
        'S2': 'What is your age?',
        'S3': 'What is your postcode?',
        'Q2': 'And which ONE of these brands is your main provider?',
        'Q3': 'Thinking about \'Origin\', how favourable is your overall impression of them?',
        'Q4a': 'How likely are you to recommend \'Origin\' to friends or family?',
        'Q4b': 'You said you would be [unlikely/likely] to recommend \'Origin\'. Why do you say that?',
        'Q6': 'In the past 12 months, have you seen or heard any advertising for \'Origin\'?',
        'D1': 'Which of the following best describes your current work status?',
        'D2': 'Which of the following best describes your total annual household income?',
        'D3': 'Which of the following best describes your household structure?',
        'Wave': 'Data collection wave',
        'CompletedDate': 'Completion date and time'
    }

    # Q1 Multi-response option text
    q1_option_texts = {
        '1': 'Synergy',
        '2': 'Western Power',
        '3': 'AGL',
        '4': 'Origin',
        '5': 'Horizon Power',
        '6': 'Red Energy',
        '97': 'Other (please specify)',
        '99': 'None of these'
    }

    # Q5 Multi-response option text
    q5_option_texts = {
        '1': 'Trustworthiness',
        '2': 'Value for money',
        '3': 'Customer service',
        '4': 'Innovation'
    }

    # Q7 Multi-response option text
    q7_option_texts = {
        '1': 'TV',
        '2': 'Online / Social media',
        '3': 'Outdoor (billboards, bus stops, etc.)',
        '4': 'Radio',
        '5': 'Print (newspaper, magazine)',
        '97': 'Other (please specify)'
    }

    # Create variable labels
    variable_labels = {
        'ID': 'Respondent ID'
    }

    # Add single-response question labels
    for var, text in question_texts.items():
        variable_labels[var] = text

    # Add Q1 multi-response labels
    q1_base_text = 'Which of the following brands of electricity providers are you aware of?'
    for code, option_text in q1_option_texts.items():
        variable_labels[f'Q1_{code}'] = f"{q1_base_text} - {option_text}"

    # Add Q5 multi-response labels
    q5_base_text = 'How would you rate \'Origin\' on each of the following?'
    for code, option_text in q5_option_texts.items():
        variable_labels[f'Q5_{code}'] = f"{q5_base_text} - {option_text}"

    # Add Q7 multi-response labels
    q7_base_text = 'Where did you see or hear advertising for \'Origin\'?'
    for code, option_text in q7_option_texts.items():
        variable_labels[f'Q7_{code}'] = f"{q7_base_text} - {option_text}"

    # Add labels for other text columns
    variable_labels.update({
        'Q1_97_Oth': 'Which of the following brands of electricity providers are you aware of? - Other (please specify)',
        'Q2_97_Oth': 'And which ONE of these brands is your main provider? - Other (please specify)',
        'Q7_97_Oth': 'Where did you see or hear advertising for \'Origin\'? - Other (please specify)',
        'D1_97_Oth': 'Which of the following best describes your current work status? - Other (please specify)',
        'D3_97_Oth': 'Which of the following best describes your household structure? - Other (please specify)'
    })

    # Value labels
    value_labels = {
        'S1': {1: 'Male', 2: 'Female', 3: 'Non-binary / Other', 99: 'Prefer not to say'},
        'S2': {2: '18-24', 3: '25-34', 4: '35-44', 5: '45-54', 6: '55-64', 7: '65+'},
        'Q2': {1: 'Synergy', 2: 'Western Power', 3: 'AGL', 4: 'Origin', 5: 'Horizon Power',
               6: 'Red Energy', 97: 'Other (please specify)', 99: 'None of these'},
        'Q3': {1: 'Very unfavourable', 2: 'Somewhat unfavourable', 3: 'Neutral',
               4: 'Somewhat favourable', 5: 'Very favourable'},
        'Q4a': {0: 'Not at all likely', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5',
                6: '6', 7: '7', 8: '8', 9: '9', 10: 'Extremely likely'},
        'Q5_1': {1: 'Very poor', 2: 'Poor', 3: 'Fair', 4: 'Good', 5: 'Excellent', 98: 'Don\'t know'},
        'Q5_2': {1: 'Very poor', 2: 'Poor', 3: 'Fair', 4: 'Good', 5: 'Excellent', 98: 'Don\'t know'},
        'Q5_3': {1: 'Very poor', 2: 'Poor', 3: 'Fair', 4: 'Good', 5: 'Excellent', 98: 'Don\'t know'},
        'Q5_4': {1: 'Very poor', 2: 'Poor', 3: 'Fair', 4: 'Good', 5: 'Excellent', 98: 'Don\'t know'},
        'Q6': {1: 'Yes', 2: 'No', 98: 'Don\'t know'},
        'D1': {1: 'Working full time', 2: 'Working part time', 3: 'Self-employed',
               4: 'Student', 5: 'Unemployed and looking for work', 6: 'Retired', 97: 'Other (please specify)'},
        'D2': {1: 'Less than $30,000', 2: '$30,000–$59,999', 3: '$60,000–$89,999',
               4: '$90,000–$119,999', 5: '$120,000–$149,999', 6: '$150,000 or more', 99: 'Prefer not to say'},
        'D3': {1: 'Live alone', 2: 'Single, no children', 3: 'Single parent with children at home',
               4: 'Couple, no children', 5: 'Couple, with children at home', 6: 'Group household / share house',
               97: 'Other (please specify)'},
        'Wave': {1: 'Week commencing 4th August', 2: 'Week commencing 11th August',
                 3: 'Week commencing 18th August', 4: 'Week commencing 25th August'}
    }

    # # Add binaroy value labels for multi-response variables
    for i in range(1, 8):
        if i == 7:  # Q7 only has 5 options
            break
        value_labels[f'Q1_{i}'] = {0: 'Not selected', 1: 'Selected'}

    value_labels['Q1_97'] = {0: 'Not selected', 1: 'Selected'}
    value_labels['Q1_99'] = {0: 'Not selected', 1: 'Selected'}

    for i in range(1, 6):
        value_labels[f'Q7_{i}'] = {0: 'Not selected', 1: 'Selected'}
    value_labels['Q7_97'] = {0: 'Not selected', 1: 'Selected'}

    return variable_labels, value_labels


def save_to_spss(df, variable_labels, value_labels, output_path):
    """
    Save as SPSS format
    """

    # Handle empty values in text columns – replace NaN with empty strings
    text_columns = [col for col in df.columns if 'Oth' in col or col == 'Q4b' or col == 'CompletedDate']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].fillna('')

    # Set data types
    for col in df.columns:
        if col in text_columns:
            # Text columns
            df[col] = df[col].astype(str)
        else:
            # Numeric columns – ensure integer type
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Convert numeric columns to integers (if possible)
            if col not in ['S3', 'Q4a']:  
                df[col] = df[col].astype('Int64') 

    # USe pyreadstat to save .sav file，with clearly defined formats
    pyreadstat.write_sav(
        df,
        output_path,
        column_labels=variable_labels,
        variable_value_labels=value_labels,
        variable_measure={
            'scale': ['Q4a', 'S3'],  # Continuous variables
            'ordinal': ['Q3', 'Q5_1', 'Q5_2', 'Q5_3', 'Q5_4', 'Wave'],  # Ordinal variables
            'nominal': [col for col in df.columns if
                        col not in ['Q4a', 'S3', 'Q3', 'Q5_1', 'Q5_2', 'Q5_3', 'Q5_4', 'Wave', 'CompletedDate']]# Nominal variables
        },
        # Explicitly define variable formats and display widths
        variable_display_width={
            'CompletedDate': 20,
            'Q4b': 200,
            'Q1_97_Oth': 100,
            'Q2_97_Oth': 100,
            'Q7_97_Oth': 100,
            'D1_97_Oth': 100,
            'D3_97_Oth': 100
        }
    )



def main():
    """
    Main execution for Task 1
    Automatically detects file paths relative to current script.
    """


    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Constructing Input and Output Paths
    input_path = os.path.join(BASE_DIR, "..", "EXAMPLE DATA FILE.xlsx")          # Path to the raw data file (one level above)
    output_sav_path = os.path.join(BASE_DIR, "cleaned_data.sav")                 # Output path for the .sav file
    output_check_path = os.path.join(BASE_DIR, "cleaned_data_check.xlsx")        # Output path for the Excel file for manual inspection

    print("📂 Input file path:", input_path)
    print("💾 Output SAV path:", output_sav_path)
    print("💾 Output Excel check path:", output_check_path)


    # Read raw data
    df = pd.read_excel(input_path)

    # Clean column names and remove leading/trailing spaces and replace non-standard quotes
    df.columns = df.columns.str.strip().str.replace('‘', "'").str.replace('’', "'")

    # Data cleaning and format conversion
    df_clean, variable_labels, value_labels = clean_and_format_data(df)

   
    # Export to SPSS file (.sav)
    save_to_spss(df_clean, variable_labels, value_labels, output_sav_path)
    print(f"✅ SAV file successfully saved: {output_sav_path}")

    
    # Display the ratio of Origin users vs. non-Origin users
    if 'Q2' in df_clean.columns:
        origin_users = (df_clean['Q2'] == 4).sum()
        non_origin_users = len(df_clean) - origin_users
        print(f"Number of Origin users: {origin_users}")
        print(f"Number of non-Origin users: {non_origin_users}")

    # Display inspection results for all text columns
    text_columns = [col for col in df_clean.columns if 'Oth' in col or col == 'Q4b']
    print(f"\nText column check:")
    for col in text_columns:
        if col in df_clean.columns:
            non_empty_count = (df_clean[col] != '').sum()
            print(f"  {col}: {non_empty_count} non-empty values")

    # Save processed Excel file for manual inspection
    df_clean.to_excel(output_check_path, index=False)
    print(f"✅ Excel check file saved: {output_check_path}")


if __name__ == "__main__":
    main()