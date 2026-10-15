import streamlit as st
import pandas as pd

def searchable_multiselect(label, options_df, key, search_column='Display_Text', 
                          value_column='Cd_CF', placeholder="Inizia a digitare..."):
    """
    Crea un componente multiselect con ricerca
    """
    
    # Container per il componente
    with st.container():
        st.write(label)
        
        # Campo di ricerca
        search_key = f"{key}_search"
        search_term = st.text_input(
            f"🔍 Cerca {label.lower()}:",
            placeholder=placeholder,
            key=search_key
        )
        
        # Filtra opzioni in base alla ricerca
        if search_term and not options_df.empty:
            filtered_options = options_df[
                options_df[search_column].str.contains(search_term, case=False, na=False)
            ].head(20)  # Limita a 20 risultati
        else:
            filtered_options = options_df.head(20) if not options_df.empty else pd.DataFrame()
        
        # Multiselect con opzioni filtrate
        if not filtered_options.empty:
            selected_display = st.multiselect(
                f"Seleziona {label.lower()}:",
                options=filtered_options[search_column].tolist(),
                key=f"{key}_select"
            )
            
            # Converti display text in codici
            selected_codes = []
            for display_text in selected_display:
                matching_row = filtered_options[filtered_options[search_column] == display_text]
                if not matching_row.empty:
                    selected_codes.append(matching_row.iloc[0][value_column])
            
            return selected_codes
        else:
            st.info("Nessuna opzione disponibile")
            return []

def include_exclude_filter(label, options_df, key_prefix, search_column='Display_Text', 
                          value_column='Cd_CF'):
    """
    Crea filtri include/exclude con ricerca
    """
    st.subheader(label)
    
    # Tabs per include/exclude
    tab1, tab2 = st.tabs(["Includi", "Escludi"])
    
    with tab1:
        st.write("Se selezioni elementi qui, verranno inclusi SOLO questi")
        include_list = searchable_multiselect(
            f"Includi {label.lower()}",
            options_df,
            f"{key_prefix}_include",
            search_column,
            value_column,
            f"Cerca {label.lower()} da includere..."
        )
    
    with tab2:
        st.write("Gli elementi selezionati qui verranno ESCLUSI")
        exclude_list = searchable_multiselect(
            f"Escludi {label.lower()}",
            options_df,
            f"{key_prefix}_exclude", 
            search_column,
            value_column,
            f"Cerca {label.lower()} da escludere..."
        )
    
    return include_list, exclude_list