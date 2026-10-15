import os

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import date, datetime
from database import DatabaseManager
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# ========================================
# STILE GLOBALE AGGRID
# ========================================
AGGRID_CUSTOM_CSS = {
    ".ag-theme-streamlit": {"--ag-font-size": "22px"},
    ".ag-header-cell-label": {"font-size": "22px !important", "font-weight": "600 !important"},
    ".ag-cell": {"font-size": "20px !important", "border-right": "1px solid #ddd !important"},
    ".ag-side-bar, .ag-side-button-label, .ag-column-select-header, .ag-column-select-column-label":
        {"font-size": "22px !important"}
}

# ========================================
# AUTENTICAZIONE - SEMPRE ALL'INIZIO
# ========================================

# Carica configurazione
from pathlib import Path
import yaml
from yaml.loader import SafeLoader

BASE_DIR = Path(__file__).resolve().parent
config_path = BASE_DIR / "auth_config.yaml"

with open(config_path, "r", encoding="utf-8") as file:
    config = yaml.load(file, Loader=SafeLoader)

# La chiave di firma del cookie non sta nel file YAML ma nel .env
config['cookie']['key'] = os.environ['AUTH_COOKIE_KEY']

# ✅ INIZIALIZZAZIONE AUTHENTICATOR v0.4.2
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# ✅ LOGIN v0.4.2 - Nuova sintassi
try:
    authenticator.login()
except Exception as e:
    st.error(f"Errore login: {e}")
    st.stop()

# ✅ Accesso alle variabili di sessione (v0.4.2)
if st.session_state.get("authentication_status"):
    # Utente autenticato
    name = st.session_state["name"]
    username = st.session_state["username"]
    
    # Ottieni ruolo da config custom
    user_role = config['user_roles'].get(username, 'contabilita')
    user_permissions = config['roles_permissions'].get(user_role, [])
    
    def has_permission(permission):
        """Verifica se l'utente ha un determinato permesso"""
        return permission in user_permissions
    
    # ========================================
    # SIDEBAR CON LOGOUT
    # ========================================
    with st.sidebar:
        st.write(f'👤 **{name}**')
        st.caption(f'📧 {config["credentials"]["usernames"][username]["email"]}')
        st.caption(f'🎭 Ruolo: **{user_role.upper()}**')
        
        # ✅ LOGOUT v0.4.2
        authenticator.logout(location='sidebar')
        st.divider()
    

    def safe_date(year, month, day):
        """Restituisce una data valida: se il giorno è troppo alto,
        usa l'ultimo del mese."""
        # Quanti giorni ha quel mese?
        last_day = calendar.monthrange(year, month)[1]
        # Se il giorno richiesto è > ultimo giorno, lo rimpiazzo
        day = min(day, last_day)
        return date(year, month, day)


    def create_universal_selector(
        df, 
        display_column, 
        code_column, 
        title, 
        search_placeholder,
        session_key_prefix,
        selected_categories=None,
        selected_marche=None,
        db_search_method=None
    ):
        """
        Selettore universale per articoli, categorie, marche, clienti, ecc.
        
        Args:
            df: DataFrame con i dati
            display_column: nome della colonna da mostrare (es: 'Display_Text')
            code_column: nome della colonna con i codici (es: 'Cd_AR')
            title: titolo del selettore
            search_placeholder: testo placeholder per la ricerca
            session_key_prefix: prefisso per le chiavi session_state (es: 'articoli_inc')
            selected_categories: filtri categorie (opzionale)
            selected_marche: filtri marche (opzionale)
            db_search_method: metodo del database per la ricerca (opzionale)
        
        Returns:
            Lista dei valori Display_Text selezionati
        """
        
        # Mostra ricerca attiva
        search_key = f"search_{session_key_prefix}_submitted"

        # Form di ricerca
        with st.form(f"search_{session_key_prefix}_form"):
            search_input = st.text_input(
                f"Cerca {title.lower()} (premi Invio):",
                value="",
                placeholder=search_placeholder,
                key=f"temp_search_{session_key_prefix}_input"
            )
            search_submitted = st.form_submit_button("Cerca")

        if search_submitted:
            if search_input.strip():
                st.session_state[search_key] = search_input
            else:
                st.session_state[search_key] = ""

        # Determina quali opzioni mostrare
        if st.session_state.get(search_key, "") and db_search_method:
            filtered_items = db_search_method(
                st.session_state[search_key],
                selected_categories=selected_categories,
                selected_marche=selected_marche
            )
            if not filtered_items.empty:
                new_options = filtered_items[display_column].tolist()
            else:
                new_options = []
                st.warning("Nessun elemento trovato")
        else:
            new_options = df[display_column].tolist()

        backup_key = f"{session_key_prefix}_backup"
        all_options = sorted(list(set(new_options + st.session_state.get(backup_key, []))))

        # Stato del selettore
        selector_key = f"show_advanced_selector_{session_key_prefix}"
        if selector_key not in st.session_state:
            st.session_state[selector_key] = False

        # Controlli principali
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if not st.session_state[selector_key]:
                if st.session_state.get(search_key, ""):
                    button_text = f"Apri Selettore Filtrato ({len(all_options)} trovati)"
                else:
                    button_text = f"Apri Selettore ({len(all_options)} disponibili)"
                
                if st.button(button_text, type="primary", key=f"open_advanced_{session_key_prefix}"):
                    st.session_state[selector_key] = True
                    st.rerun()

        with col2:
            current_selected = len(st.session_state.get(backup_key, []))
            st.metric("Selezionati", current_selected)

        with col3:
            if st.session_state[selector_key]:
                if st.button("Chiudi Selettore", key=f"close_advanced_{session_key_prefix}"):
                    st.session_state[selector_key] = False
                    st.rerun()

        # Resoconto elementi selezionati
        current_selected_list = st.session_state.get(backup_key, [])
        if current_selected_list:
            with st.expander(f"Vedi {title.lower()} selezionati ({len(current_selected_list)})"):
                selected_df = pd.DataFrame({title: current_selected_list})
                st.dataframe(selected_df, width='stretch', hide_index=True)
                
                col_remove1, col_remove2 = st.columns([2, 1])
                with col_remove1:
                    to_remove = st.selectbox(
                        f"Rimuovi {title.lower()}:",
                        options=[''] + current_selected_list,
                        key=f"remove_single_{session_key_prefix}"
                    )
                with col_remove2:
                    if st.button("Rimuovi", key=f"remove_single_{session_key_prefix}_btn") and to_remove:
                        current_selected_list.remove(to_remove)
                        st.session_state[backup_key] = current_selected_list
                        st.rerun()

        # Selettore avanzato
        if st.session_state[selector_key]:
            st.divider()
            
            available_df = df[df[display_column].isin(all_options)]
            
            selected_items = create_advanced_item_selector(
                df=available_df,
                display_column=display_column,
                code_column=code_column,
                title=f"Seleziona {title}",
                selected_items=st.session_state.get(backup_key, []),
                key_suffix=session_key_prefix
            )
            
            st.divider()
            
            col_save, col_cancel, col_clear = st.columns([1, 1, 1])
            with col_save:
                if st.button("Salva e Chiudi", type="primary", key=f"save_{session_key_prefix}_selection"):
                    current_backup = st.session_state.get(backup_key, [])
                    combined_selection = list(set(current_backup + selected_items))
                    st.session_state[backup_key] = combined_selection
                    st.session_state[selector_key] = False
                    st.success(f"Aggiunti {len(selected_items)} nuovi elementi. Totale: {len(combined_selection)}")
                    st.rerun()
            
            with col_cancel:
                if st.button("Annulla", key=f"cancel_{session_key_prefix}_selection"):
                    st.session_state[selector_key] = False
                    st.rerun()
            
            with col_clear:
                if st.button("Pulisci Selezione", key=f"clear_{session_key_prefix}_selection"):
                    st.session_state[backup_key] = []
                    st.session_state[selector_key] = False
                    st.success("Selezione pulita")
                    st.rerun()

        return st.session_state.get(backup_key, [])

    def create_advanced_item_selector(df, display_column, code_column, title, selected_items=[], key_suffix=""):
        """
        Crea selettore AgGrid generico per qualsiasi tipo di dato
        """
        st.write(f"**{title}**")
        
        col_info1, col_info2, col_controls = st.columns([1, 1, 1])
        with col_info1:
            st.metric("Disponibili", len(df))
        with col_info2:
            st.metric("Selezionati", len(selected_items))
        with col_controls:
            expand_mode = st.selectbox(
                "Altezza:",
                options=["Normale", "Grande", "Molto Grande"],
                key=f"size_mode_{key_suffix}"
            )
        
        if df.empty:
            st.warning("Nessun elemento disponibile")
            return selected_items

        # Escludi elementi già selezionati
        available_df = df[~df[display_column].isin(selected_items)].copy()
        
        if available_df.empty:
            st.info("Tutti gli elementi disponibili sono già stati selezionati")
            return selected_items
        
        # Prepara per AgGrid
        grid_df = available_df[[code_column, display_column]].copy()
        
        # Per articoli, separa codice e descrizione
        if display_column == 'Display_Text' and ' - ' in str(grid_df[display_column].iloc[0]):
            grid_df['Solo_Descrizione'] = grid_df[display_column].str.split(' - ', n=1, expand=True)[1]
            grid_df['Solo_Descrizione'] = grid_df['Solo_Descrizione'].fillna(grid_df[display_column])
            grid_df = grid_df.rename(columns={
                code_column: 'Codice',
                'Solo_Descrizione': 'Descrizione'
            })
            display_cols = ['Codice', 'Descrizione']
        else:
            grid_df = grid_df.rename(columns={
                code_column: 'Codice',
                display_column: 'Nome'
            })
            display_cols = ['Codice', 'Nome']
        
        grid_df = grid_df[display_cols].copy().reset_index(drop=True)

        # Configurazione AgGrid
        gb = GridOptionsBuilder.from_dataframe(grid_df)
        gb.configure_selection('multiple', use_checkbox=True, header_checkbox=True)
        gb.configure_column(display_cols[0], width=100, pinned="left")
        gb.configure_column(display_cols[1], flex=1)
        gb.configure_grid_options(domLayout='normal', suppressRowDeselection=False, rowMultiSelectWithClick=True)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True)
        
        gridOptions = gb.build()

        # Altezza dinamica
        grid_height = {"Normale": 400, "Grande": 600, "Molto Grande": 800}[expand_mode]
        
        grid_response = AgGrid(
            grid_df,
            gridOptions=gridOptions,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_on=["selectionChanged"],
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=False,
            height=grid_height,
            width='stretch',
            key=f"grid_{key_suffix}",
            allow_unsafe_jscode=True
        )

        
        # Estrai selezioni
        selected_rows = grid_response['selected_rows']
        if selected_rows is not None and not selected_rows.empty:
            if len(display_cols) == 2 and display_cols[1] == 'Descrizione':
                # Ricostruisci Display_Text per articoli
                return [f"{row[display_cols[0]]} - {row[display_cols[1]]}" for _, row in selected_rows.iterrows()]
            else:
                # Per altri tipi, usa la colonna Nome direttamente  
                return selected_rows[display_cols[1]].tolist()
        
        return []

    # Aggiungi questa funzione helper prima di create_filters()
    def search_clienti_wrapper(search_term, selected_categories=None, selected_marche=None):
        """Wrapper per search_clienti che ignora i parametri non supportati"""
        db = init_database()
        return db.search_clienti(search_term)  # Passa solo il termine di ricerca


    def handle_excel_upload_articoli(db, selected_categorie_codes=None, selected_marche_codes=None):
        """
        Gestisce l'upload di un file Excel contenente codici articolo
        e aggiorna gli stati Include/Exclude in session_state.
        """
        st.write("**Carica Excel con codici articolo**")
        uploaded_file = st.file_uploader(
            "Seleziona file Excel:",
            type=['xlsx', 'xls'],
            help="Il file deve contenere una colonna 'Cd_AR' con i codici articolo",
            key="excel_upload_articoli"
        )

        if uploaded_file is not None:
            try:
                df_excel = pd.read_excel(uploaded_file)

                if 'Cd_AR' in df_excel.columns:
                    # Estrai i codici unici
                    codici_excel = (
                        df_excel['Cd_AR']
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .unique()
                        .tolist()
                    )

                    if codici_excel:
                        st.info(f"Trovati {len(codici_excel)} codici nel file Excel")

                        codici_validi, codici_non_trovati = [], []

                        for codice in codici_excel:
                            articolo_match = db.search_articoli(
                                codice,
                                selected_categories=selected_categorie_codes if selected_categorie_codes else None,
                                selected_marche=selected_marche_codes if selected_marche_codes else None
                            )

                            if not articolo_match.empty:
                                exact_match = articolo_match[articolo_match['Cd_AR'] == codice]
                                if not exact_match.empty:
                                    codici_validi.append(exact_match.iloc[0]['Display_Text'])
                                else:
                                    codici_non_trovati.append(codice)
                            else:
                                codici_non_trovati.append(codice)

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("➕ Aggiungi a Include", type="primary"):
                                current_include = st.session_state.get("articoli_inc_backup", [])
                                new_include = list(set(current_include + codici_validi))
                                st.session_state.articoli_inc_backup = new_include
                                if "articoli_include_multiselect" in st.session_state:
                                    del st.session_state["articoli_include_multiselect"]
                                st.success(f"Aggiunti {len(codici_validi)} articoli alla selezione Include")
                                st.rerun()

                        with col2:
                            if st.button("➖ Aggiungi a Exclude", type="secondary"):
                                current_exclude = st.session_state.get("articoli_exc_backup", [])
                                new_exclude = list(set(current_exclude + codici_validi))
                                st.session_state.articoli_exc_backup = new_exclude
                                if "articoli_exclude_multiselect" in st.session_state:
                                    del st.session_state["articoli_exclude_multiselect"]
                                st.success(f"Aggiunti {len(codici_validi)} articoli alla selezione Exclude")
                                st.rerun()

                        if codici_validi:
                            st.success(f"✅ {len(codici_validi)} codici validi trovati")
                            with st.expander("Mostra codici validi"):
                                for codice in codici_validi:
                                    st.text(codice)

                        if codici_non_trovati:
                            st.warning(f"⚠️ {len(codici_non_trovati)} codici non trovati")
                            with st.expander("Mostra codici non trovati"):
                                for codice in codici_non_trovati:
                                    st.text(codice)

                    else:
                        st.error("Nessun codice articolo valido trovato nel file")
                else:
                    st.error("Il file deve contenere una colonna chiamata 'Cd_AR'")
                    st.info("Colonne trovate: " + ", ".join(df_excel.columns.tolist()))

            except Exception as e:
                st.error(f"Errore nella lettura del file: {str(e)}")
                st.info("Assicurati che il file sia un Excel valido con una colonna 'Cd_AR'")

        # Mostra un esempio di formato richiesto
        st.write("**Formato file richiesto:**")
        example_df = pd.DataFrame({'Cd_AR': ['ART003', 'ART004', 'ART005']})
        st.dataframe(example_df, hide_index=True)

    # Configurazione pagina
    st.set_page_config(
        page_title="Analisi Magazzino",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Inizializzazione database
    @st.cache_resource
    def init_database():
        return DatabaseManager()

    def load_filter_data():
        """Carica i dati per i filtri"""
        db = init_database()
        
        magazzini = db.get_magazzini_list_with_descriptions()
        categorie = db.get_categorie_list()
        articoli = db.get_articoli_list()
        clienti = db.get_clienti_list()
        
        return magazzini, categorie, articoli, clienti

    def create_top_articles_chart(filters):
        """Crea grafico Top 20 Articoli con congelamento - Approccio callback"""
        
        # Inizializza SOLO se non esistono
        if 'articles_data' not in st.session_state:
            st.session_state.articles_data = None
        if 'articles_filters' not in st.session_state:
            st.session_state.articles_filters = None
        if 'articles_frozen' not in st.session_state:
            st.session_state.articles_frozen = False
        
        # Funzione callback per congelare/scongelare
        def toggle_freeze():
            if not st.session_state.articles_frozen:
                # ✅ Congela → carica e salva dati
                db = init_database()
                chart_data = db.get_top_articles_chart(
                    date_from=filters['date_from'],
                    date_to=filters['date_to'],
                    limit=20,
                    exclude_obsolete=filters['exclude_obsolete'],
                    exclude_attribute_18=filters['exclude_attribute_18'],
                    magazzini=filters['magazzini'],
                    categorie=filters['categorie'],
                    marche=filters['marche'],
                    articoli_include=filters['articoli_include'],
                    articoli_exclude=filters['articoli_exclude'],
                    clienti_include=filters['clienti_include'],
                    clienti_exclude=filters['clienti_exclude']
                )
                st.session_state.articles_data = chart_data
                st.session_state.articles_filters = filters.copy()
            else:
                # ❌ Scongela → pulisci
                st.session_state.articles_data = None
                st.session_state.articles_filters = None
            
            # Inverti lo stato
            st.session_state.articles_frozen = not st.session_state.articles_frozen
        
        # 🔘 Pulsante toggle
        button_text = "💧 Scongela Articoli" if st.session_state.articles_frozen else "❄️ Congela Dati"
        st.button(button_text, on_click=toggle_freeze, key="articles_freeze_btn")
        
        # 📊 Determina quali dati usare
        if st.session_state.articles_frozen and st.session_state.articles_data is not None:
            chart_data = st.session_state.articles_data
            frozen_filters = st.session_state.articles_filters
            
            # Expander con filtri congelati
            with st.expander("Riepilogo filtri usati", expanded=False):
                st.write("**Periodo:** ", f"{frozen_filters.get('date_from')} - {frozen_filters.get('date_to')}")
                
                if frozen_filters.get('magazzini'):
                    st.write("**Magazzini:** ", ', '.join(frozen_filters['magazzini']))
                
                if frozen_filters.get('categorie'):
                    db = init_database()
                    categorie_df = db.get_categorie_list()
                    categorie_desc = []
                    for cod_cat in frozen_filters['categorie']:
                        match = categorie_df[categorie_df['Cd_ARGruppo1'] == cod_cat]
                        categorie_desc.append(match.iloc[0]['Descrizione'] if not match.empty else cod_cat)
                    st.write("**Categorie:** ", ', '.join(categorie_desc))
                
                if frozen_filters.get('marche'):
                    db = init_database()
                    marche_df = db.get_marche_list()
                    marche_desc = []
                    for cod_marca in frozen_filters['marche']:
                        match = marche_df[marche_df['Cd_ARMarca'] == cod_marca]
                        marche_desc.append(match.iloc[0]['Descrizione'] if not match.empty else cod_marca)
                    st.write("**Marche:** ", ', '.join(marche_desc))
                
                if frozen_filters.get('articoli_include'):
                    st.write("**Articoli inclusi:** ", f"{len(frozen_filters['articoli_include'])} selezionati")
                
                if frozen_filters.get('articoli_exclude'):
                    st.write("**Articoli esclusi:** ", f"{len(frozen_filters['articoli_exclude'])} selezionati")
                
                if frozen_filters.get('clienti_include'):
                    st.write("**Clienti inclusi:** ", f"{len(frozen_filters['clienti_include'])} selezionati")
                
                if frozen_filters.get('clienti_exclude'):
                    st.write("**Clienti esclusi:** ", f"{len(frozen_filters['clienti_exclude'])} selezionati")
                
                st.write("**Esclude obsoleti:** ", "Sì" if frozen_filters.get('exclude_obsolete') else "No")
                st.write("**Esclude attributo 18:** ", "Sì" if frozen_filters.get('exclude_attribute_18') else "No")
        else:
            # 📊 Carica dati freschi se non congelato
            db = init_database()
            chart_data = db.get_top_articles_chart(
                date_from=filters['date_from'],
                date_to=filters['date_to'],
                limit=20,
                exclude_obsolete=filters['exclude_obsolete'],
                exclude_attribute_18=filters['exclude_attribute_18'],
                magazzini=filters['magazzini'],
                categorie=filters['categorie'],
                marche=filters['marche'],
                articoli_include=filters['articoli_include'],
                articoli_exclude=filters['articoli_exclude'],
                clienti_include=filters['clienti_include'],
                clienti_exclude=filters['clienti_exclude']
            )
        
        # 🎨 Mostra grafico
        show_articles_chart(chart_data)


    def create_top_clients_chart(filters):
        """Crea grafico Top 20 Clienti con congelamento - Approccio callback"""
        
        # Inizializza session state solo se non esiste
        if 'clients_data' not in st.session_state:
            st.session_state.clients_data = None
        if 'clients_filters' not in st.session_state:
            st.session_state.clients_filters = None
        if 'clients_frozen' not in st.session_state:
            st.session_state.clients_frozen = False
        
        # Funzione callback per toggle
        def toggle_freeze():
            if not st.session_state.clients_frozen:
                # ✅ Congela: carica e salva dati
                db = init_database()
                chart_data = db.get_top_clients_chart(
                    date_from=filters['date_from'],
                    date_to=filters['date_to'],
                    limit=20,
                    exclude_obsolete=filters['exclude_obsolete'],
                    exclude_attribute_18=filters['exclude_attribute_18'],
                    magazzini=filters['magazzini'],
                    categorie=filters['categorie'],
                    marche=filters['marche'],
                    articoli_include=filters['articoli_include'],
                    articoli_exclude=filters['articoli_exclude'],
                    clienti_include=filters['clienti_include'],
                    clienti_exclude=filters['clienti_exclude']
                )
                st.session_state.clients_data = chart_data
                st.session_state.clients_filters = filters.copy()
            else:
                # ❌ Scongela: reset
                st.session_state.clients_data = None
                st.session_state.clients_filters = None
            
            # Inverti stato
            st.session_state.clients_frozen = not st.session_state.clients_frozen
        
        # 🔘 Pulsante toggle
        button_text = "💧 Scongela Clienti" if st.session_state.clients_frozen else "❄️ Congela Dati"
        st.button(button_text, on_click=toggle_freeze, key="clients_freeze_btn")
        
        # 📊 Dati da usare
        if st.session_state.clients_frozen and st.session_state.clients_data is not None:
            chart_data = st.session_state.clients_data
            frozen_filters = st.session_state.clients_filters
            
            # Expander riepilogo filtri
            with st.expander("Riepilogo filtri usati", expanded=False):
                st.write("**Periodo:** ", f"{frozen_filters.get('date_from')} - {frozen_filters.get('date_to')}")
                
                if frozen_filters.get('magazzini'):
                    st.write("**Magazzini:** ", ', '.join(frozen_filters['magazzini']))
                
                if frozen_filters.get('categorie'):
                    db = init_database()
                    categorie_df = db.get_categorie_list()
                    categorie_desc = []
                    for cod_cat in frozen_filters['categorie']:
                        match = categorie_df[categorie_df['Cd_ARGruppo1'] == cod_cat]
                        categorie_desc.append(match.iloc[0]['Descrizione'] if not match.empty else cod_cat)
                    st.write("**Categorie:** ", ', '.join(categorie_desc))
                
                if frozen_filters.get('marche'):
                    db = init_database()
                    marche_df = db.get_marche_list()
                    marche_desc = []
                    for cod_marca in frozen_filters['marche']:
                        match = marche_df[marche_df['Cd_ARMarca'] == cod_marca]
                        marche_desc.append(match.iloc[0]['Descrizione'] if not match.empty else cod_marca)
                    st.write("**Marche:** ", ', '.join(marche_desc))
                
                if frozen_filters.get('articoli_include'):
                    st.write("**Articoli inclusi:** ", f"{len(frozen_filters['articoli_include'])} selezionati")
                
                if frozen_filters.get('articoli_exclude'):
                    st.write("**Articoli esclusi:** ", f"{len(frozen_filters['articoli_exclude'])} selezionati")

                if frozen_filters.get('clienti_include'):
                    st.write("**Clienti inclusi:** ", f"{len(frozen_filters['clienti_include'])} selezionati")
                
                if frozen_filters.get('clienti_exclude'):
                    st.write("**Clienti esclusi:** ", f"{len(frozen_filters['clienti_exclude'])} selezionati")
                
                st.write("**Esclude obsoleti:** ", "Sì" if frozen_filters.get('exclude_obsolete') else "No")
                st.write("**Esclude attributo 18:** ", "Sì" if frozen_filters.get('exclude_attribute_18') else "No")
        
        else:
            # 📊 Dati freschi
            db = init_database()
            chart_data = db.get_top_clients_chart(
                date_from=filters['date_from'],
                date_to=filters['date_to'],
                limit=20,
                exclude_obsolete=filters['exclude_obsolete'],
                exclude_attribute_18=filters['exclude_attribute_18'],
                magazzini=filters['magazzini'],
                categorie=filters['categorie'],
                marche=filters['marche'],
                articoli_include=filters['articoli_include'],
                articoli_exclude=filters['articoli_exclude']
            )
        
        # 🎨 Mostra grafico
        show_clients_chart(chart_data)

    def show_clients_chart(chart_data):
        """Mostra grafico Top Clienti"""
        if chart_data is None or chart_data.empty:
            st.warning("📊 Nessun dato disponibile per il grafico clienti")
            return
        
        import plotly.express as px
        
        # Calcola la somma totale
        total_value = chart_data['Valore_Totale'].sum()
        
        fig = px.bar(
            chart_data,
            x='Valore_Totale',
            y='Display_Label',
            orientation='h',
            title="🏆 Top 20 Clienti per Valore Venduto",
            color='Valore_Totale',
            color_continuous_scale='Viridis',
            hover_data={
                'Num_Articoli_Diversi': True,
                'Display_Label': False
            }
        )
        
        fig.update_layout(
            height=700,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending', 'title': None},  # Rimuovi titolo asse Y
            xaxis_tickformat=',.0f',
            xaxis_title=f'Somma Totale: €{total_value:,.2f}',  # Imposta titolo asse X
            hoverlabel=dict(bgcolor="white", font_size=12),
            title_x=0.5,
            dragmode='pan'
        )
        
        config = {'scrollZoom': True}

        fig.update_traces(
            texttemplate='€%{x:,.0f}',
            textposition='outside',
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                        'Valore: €%{x:,.2f}<br>' +
                        'Articoli diversi: %{customdata[1]}<extra></extra>',
            customdata=chart_data[['Display_Label', 'Num_Articoli_Diversi']].values
        )
        
        st.plotly_chart(fig, width='stretch', config=config)

    def show_articles_chart(chart_data):
        """Mostra grafico Top Articoli"""
        if chart_data is None or chart_data.empty:
            st.warning("📊 Nessun dato disponibile per il grafico articoli")
            return
        
        import plotly.express as px
        
        # Calcola la somma totale
        total_value = chart_data['Valore_Totale'].sum()
        
        # Crea grafico a barre orizzontali
        fig = px.bar(
            chart_data,
            x='Valore_Totale',
            y='Display_Label',
            orientation='h',
            title="🏆 Top 20 Articoli per Valore Venduto",
            # Rimuovi labels da qui
            color='Valore_Totale',
            color_continuous_scale='RdYlBu_r',
            hover_data={
                'Categoria': True,
                'Marca': True,
                'Quantita_CF': ':.2f',
                'Display_Label': False
            }
        )
        
        # Personalizzazione grafico
        fig.update_layout(
            height=700,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending', 'title': None},  # Rimuovi titolo asse Y
            xaxis_tickformat=',.0f',
            xaxis_title=f'Somma Totale: €{total_value:,.2f}',  # Imposta titolo asse X
            hoverlabel=dict(bgcolor="white", font_size=12),
            title_x=0.5,
            dragmode='pan'
        )
        
        config = {'scrollZoom': True}

        # Formatta valori sull'asse X
        fig.update_traces(
            texttemplate='€%{x:,.0f}',
            textposition='outside',
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                        'Valore: €%{x:,.2f}<br>' +
                        'Categoria: %{customdata[1]}<br>' +
                        'Marca: %{customdata[2]}<br>' +
                        'Quantità CF: %{customdata[3]}<extra></extra>',
            customdata=chart_data[['Display_Label', 'Categoria', 'Marca', 'Quantita_CF']].values
        )
        
        st.plotly_chart(fig, width='stretch', config=config)

    def create_filters():
        """Crea i filtri nella sidebar con backup delle selezioni"""
        st.sidebar.header("Filtri")
        
        # Session state per le ricerche
        if 'search_marca_submitted' not in st.session_state:
            st.session_state.search_marca_submitted = ""
        if 'search_articolo_inc_submitted' not in st.session_state:
            st.session_state.search_articolo_inc_submitted = ""
        if 'search_articolo_exc_submitted' not in st.session_state:
            st.session_state.search_articolo_exc_submitted = ""
        if 'search_cliente_inc_submitted' not in st.session_state:
            st.session_state.search_cliente_inc_submitted = ""
        if 'search_cliente_exc_submitted' not in st.session_state:
            st.session_state.search_cliente_exc_submitted = ""
        
        # Session state per backup delle selezioni
        if 'marche_backup' not in st.session_state:
            st.session_state.marche_backup = []
        if 'articoli_inc_backup' not in st.session_state:
            st.session_state.articoli_inc_backup = []
        if 'articoli_exc_backup' not in st.session_state:
            st.session_state.articoli_exc_backup = []
        if 'clienti_inc_backup' not in st.session_state:
            st.session_state.clienti_inc_backup = []
        if 'clienti_exc_backup' not in st.session_state:
            st.session_state.clienti_exc_backup = []
        
        # Filtri date
        with st.sidebar.expander("📅 Date", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                raw_from = st.date_input("Da:", value=datetime.now().date(), key="date_from")
            with col2:
                raw_to = st.date_input("A:", value=datetime.now().date(), key="date_to")

        # Validazione date (es. se utente scrive 30/02)
        date_from = safe_date(raw_from.year, raw_from.month, raw_from.day)
        date_to   = safe_date(raw_to.year, raw_to.month, raw_to.day)
        # print(date_from, date_to)
        
        # Carica dati per filtri
        db = init_database()
        magazzini_df = db.get_magazzini_list_with_descriptions()
        categorie_df = db.get_categorie_list()
        articoli_df = db.get_articoli_list()
        clienti_df = db.get_clienti_list()
        marche_df = db.get_marche_list()
        
        # Filtro magazzini
        selected_magazzini = []
        if not magazzini_df.empty:
            with st.sidebar.expander("📦 Magazzini", expanded=False):  # 👈 menu a discesa
                default_magazzino = magazzini_df[magazzini_df['Cd_MG'] == '00002']['Display_Text'].tolist()
                
                selected_magazzini_display = st.multiselect(
                    "Seleziona magazzini:",
                    options=magazzini_df['Display_Text'].tolist(),
                    default=default_magazzino,
                    key="magazzini"
                )
                
                for display in selected_magazzini_display:
                    matching = magazzini_df[magazzini_df['Display_Text'] == display]
                    if not matching.empty:
                        selected_magazzini.append(matching.iloc[0]['Cd_MG'])

            
        # =========================
        # Filtro categorie
        # =========================
        selected_categorie_codes = []
        if not categorie_df.empty:
            with st.sidebar.expander("🔖 Categorie", expanded=False):
                # 1. Backup selezioni attuali (prima del rerun)
                current_categorie = st.session_state.get("categorie", [])
                if current_categorie:
                    st.session_state.categorie_backup = current_categorie

                # Carica SEMPRE tutte le categorie disponibili
                categorie_df = db.get_categorie_list()  # Senza filtri di marche

                if not categorie_df.empty:
                    # 3. Unisci categorie DB + backup
                    all_options_categorie = sorted(list(set(
                        categorie_df['Descrizione'].tolist() + st.session_state.get("categorie_backup", [])
                    )))

                    # 4. Multiselect con default sul backup
                    selected_categorie_desc = st.multiselect(
                        "Seleziona categorie:",
                        options=all_options_categorie,
                        default=st.session_state.get("categorie_backup", []),
                        key="categorie"
                    )

                    # 5. Conversione descrizione → codice
                    for desc in selected_categorie_desc:
                        matching_cat = categorie_df[categorie_df['Descrizione'] == desc]
                        if not matching_cat.empty:
                            selected_categorie_codes.append(matching_cat.iloc[0]['Cd_ARGruppo1'])



        # =========================
        # Filtro marche con filtro categorie dinamico
        # =========================
        selected_marche = []
        if not marche_df.empty:
            with st.sidebar.expander("🏭 Marche", expanded=False):
                # 🔹 1. Backup selezioni attuali (prima del rerun)
                current_widget_value = st.session_state.get("marche_multiselect", [])
                if current_widget_value:
                    st.session_state.marche_backup = current_widget_value

                # 🔹 2. Form di ricerca
                with st.form("search_marca_form"):
                    search_marca_input = st.text_input(
                        "Cerca marca (premi Invio per filtrare):",
                        value=st.session_state.search_marca_submitted,
                        placeholder="Inizia a digitare e premi Invio..."
                    )
                    search_marca_submitted = st.form_submit_button("Cerca")

                if search_marca_submitted:
                    st.session_state.search_marca_submitted = search_marca_input

                # 🔹 3. Logica di ricerca marche
                if st.session_state.search_marca_submitted:
                    if st.session_state.search_marca_submitted.strip():
                        filtered_marche = db.search_marche(
                            st.session_state.search_marca_submitted,
                            selected_categories=selected_categorie_codes
                        )
                    else:
                        filtered_marche = db.get_marche_list(selected_categories=selected_categorie_codes)

                    if not filtered_marche.empty:
                        new_options = filtered_marche['Descrizione'].tolist()
                        search_text = st.session_state.search_marca_submitted.strip()
                        if search_text:
                            st.info(f"Trovate {len(new_options)} marche per '{search_text}'")
                        else:
                            st.info(f"Mostrate {len(new_options)} marche")
                        if selected_categorie_codes:
                            st.info(f"Filtrate per categorie selezionate")
                    else:
                        st.warning("Nessuna marca trovata")
                        new_options = []
                else:
                    if selected_categorie_codes:
                        marche_filtrate = db.get_marche_list(selected_categories=selected_categorie_codes)
                        new_options = marche_filtrate['Descrizione'].tolist()
                        if new_options:
                            st.info(f"Marche filtrate per categorie selezionate ({len(new_options)} disponibili)")
                    else:
                        new_options = marche_df['Descrizione'].tolist()

                # 🔹 4. Unisci marche DB + backup
                all_options_marche = sorted(list(set(
                    new_options + st.session_state.get("marche_backup", [])
                )))

                # 🔹 5. Multiselect con default sul backup
                selected_marche_desc = st.multiselect(
                    "Seleziona marche:",
                    options=all_options_marche,
                    default=st.session_state.get("marche_backup", []),
                    key="marche_multiselect"
                )

                # 🔹 6. Conversione descrizione → codice
                for desc in selected_marche_desc:
                    matching_marca = marche_df[marche_df['Descrizione'] == desc]
                    if not matching_marca.empty:
                        selected_marche.append(matching_marca.iloc[0]['Cd_ARMarca'])


            
    # Filtri articoli con filtro categorie dinamico
        with st.sidebar.expander("🏷️ Articoli", expanded=False):
            articoli_include_display, articoli_exclude_display = [], []
            articoli_include, articoli_exclude = [], []
            articoli_df = db.get_articoli_list(
                selected_categories=selected_categorie_codes if selected_categorie_codes else None,
                selected_marche=selected_marche if selected_marche else None
            )

            if not articoli_df.empty:
                tab_inc, tab_exc, tab_upload = st.tabs(["Includi", "Escludi", "Upload Excel"])

                # --- TAB INCLUDE ---
                with tab_inc:
                    articoli_include_display = create_universal_selector(
                        df=articoli_df,
                        display_column='Display_Text',
                        code_column='Cd_AR',
                        title="Articoli da Includere",
                        search_placeholder="Codice o descrizione...",
                        session_key_prefix="articoli_inc",
                        selected_categories=selected_categorie_codes,
                        selected_marche=selected_marche,
                        db_search_method=db.search_articoli
                    )

                # --- TAB ESCLUDE ---
                with tab_exc:
                    articoli_exclude_display = create_universal_selector(
                        df=articoli_df,
                        display_column='Display_Text',
                        code_column='Cd_AR',
                        title="Articoli da Escludere",
                        search_placeholder="Codice o descrizione...",
                        session_key_prefix="articoli_exc",
                        selected_categories=selected_categorie_codes,
                        selected_marche=selected_marche,
                        db_search_method=db.search_articoli
                    )
            
                # --- TAB UPLOAD EXCEL ---
                with tab_upload:
                    handle_excel_upload_articoli(
                        db=db,
                        selected_categorie_codes=selected_categorie_codes,
                        selected_marche_codes=selected_marche
                    )

            # Conversione in codici - Include
            articoli_include_display = st.session_state.get("articoli_inc_backup", [])
            for display in articoli_include_display:
                matching = articoli_df[articoli_df['Display_Text'] == display]
                if not matching.empty:
                    articoli_include.append(matching.iloc[0]['Cd_AR'])

            # Conversione in codici - Exclude
            articoli_exclude_display = st.session_state.get("articoli_exc_backup", [])
            for display in articoli_exclude_display:
                matching = articoli_df[articoli_df['Display_Text'] == display]
                if not matching.empty:
                    articoli_exclude.append(matching.iloc[0]['Cd_AR'])
            
        # Normalizzazione articoli include/exclude
        if not articoli_include:  
            articoli_include = None   # Nessun filtro = tutti
        if not articoli_exclude:  
            articoli_exclude = None

    # Filtri clienti con backup
        clienti_include, clienti_exclude = [], []
        with st.sidebar.expander("👥 Clienti", expanded=False):
            if not clienti_df.empty:
                tab_inc_cli, tab_exc_cli = st.tabs(["Includi", "Escludi"])
                
                with tab_inc_cli:
                    clienti_include_display = create_universal_selector(
                        df=clienti_df,
                        display_column='Display_Text',
                        code_column='Cd_CF',
                        title="Clienti da Includere",
                        search_placeholder="Codice o ragione sociale...",
                        session_key_prefix="clienti_inc",
                        selected_categories=None,  # I clienti non hanno filtri per categorie/marche
                        selected_marche=None,
                        db_search_method=search_clienti_wrapper 
                    )
                
                with tab_exc_cli:
                    clienti_exclude_display = create_universal_selector(
                        df=clienti_df,
                        display_column='Display_Text',
                        code_column='Cd_CF',
                        title="Clienti da Escludere",
                        search_placeholder="Codice o ragione sociale...",
                        session_key_prefix="clienti_exc",
                        selected_categories=None,
                        selected_marche=None,
                        db_search_method=search_clienti_wrapper 
                    )
            else:
                clienti_include_display = []
                clienti_exclude_display = []

            # Conversione in codici - Clienti Include
            clienti_include_display = st.session_state.get("clienti_inc_backup", [])
            for display in clienti_include_display:
                matching = clienti_df[clienti_df['Display_Text'] == display]
                if not matching.empty:
                    clienti_include.append(matching.iloc[0]['Cd_CF'])

            # Conversione in codici - Clienti Exclude
            clienti_exclude_display = st.session_state.get("clienti_exc_backup", [])
            for display in clienti_exclude_display:
                matching = clienti_df[clienti_df['Display_Text'] == display]
                if not matching.empty:
                    clienti_exclude.append(matching.iloc[0]['Cd_CF'])

        if not clienti_include:
            clienti_include = None
        if not clienti_exclude:
            clienti_exclude = None

        
        # # Filtri soglie
        # with st.sidebar.expander("⚙️ Soglie", expanded=False):
        #     enable_soglie = st.checkbox(
        #         "Abilita filtri soglie",
        #         value=False,
        #         key="enable_soglie",
        #         help="Attiva per utilizzare i filtri di giacenza"
        #     )

        #     min_giacenza = st.number_input(
        #         "Giacenza minima (CF):",
        #         min_value=0.0,
        #         value=0.0,
        #         step=0.1,
        #         key="min_giacenza",
        #         disabled=not enable_soglie
        #     )

        #     max_giacenza = st.number_input(
        #         "Giacenza massima (CF):",
        #         min_value=0.0,
        #         value=0.0,
        #         step=0.1,
        #         key="max_giacenza",
        #         disabled=not enable_soglie,
        #         help="Impostare a 0 per non applicare limite massimo"
        #     )

        #     if not enable_soglie:
        #         st.caption("⚠️ Filtri soglie disabilitati - tutti gli articoli saranno mostrati")


        # Dopo il checkbox "Includi tutti gli articoli", aggiungi:
        exclude_obsolete = st.sidebar.checkbox(
            "Escludi articoli obsoleti",
            value=False,  # Default attivo (comportamento attuale)
            help="Se disattivato, includerà anche articoli contrassegnati come obsoleti su ARCA"
        )

        exclude_attribute_18 = st.sidebar.checkbox(
            "Escludi articoli con attributo 18",
            value=False,  # Default attivo (comportamento attuale)
            help="Se disattivato, includerà anche articoli contrassegnati per l'esclusione dalle stampe"
        )

        # Pulsante per reset tutti i filtri
        st.sidebar.subheader("Reset")
        if st.sidebar.button("Azzera Tutti i Filtri", type="primary"):
            # Reset backup selezioni
            st.session_state.categorie_backup = []
            st.session_state.marche_backup = []
            st.session_state.articoli_inc_backup = []
            st.session_state.articoli_exc_backup = []
            st.session_state.clienti_inc_backup = []
            st.session_state.clienti_exc_backup = []
            
            # Reset ricerche
            st.session_state.search_marca_submitted = ""
            st.session_state.search_articolo_inc_submitted = ""
            st.session_state.search_articolo_exc_submitted = ""
            st.session_state.search_cliente_inc_submitted = ""
            st.session_state.search_cliente_exc_submitted = ""
            
            # Reset widget keys
            for key in ["categorie","marche_multiselect", "articoli_include_multiselect", 
                    "articoli_exclude_multiselect", "clienti_include_multiselect", 
                    "clienti_exclude_multiselect"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.rerun()
        
        return {
            'date_from': date_from,
            'date_to': date_to,
            'magazzini': selected_magazzini if selected_magazzini else None,
            "categorie": selected_categorie_codes if selected_categorie_codes else None,
            "marche": selected_marche if selected_marche else None,
            "articoli_include": articoli_include,
            "articoli_exclude": articoli_exclude,
            'has_excel_include': bool(st.session_state.get("articoli_inc_backup", [])),
            'has_excel_exclude': bool(st.session_state.get("articoli_exc_backup", [])),   
            'clienti_include': clienti_include if clienti_include else None,
            'clienti_exclude': clienti_exclude if clienti_exclude else None,
            # 'enable_soglie': enable_soglie,  
            # 'min_giacenza': min_giacenza,
            # 'max_giacenza': max_giacenza,
            'exclude_obsolete': exclude_obsolete,
            'exclude_attribute_18': exclude_attribute_18
        }

    def create_summary_cards(filters):
        """Crea le cards di riepilogo con congelamento e dettaglio articoli automatico"""
        
        # Inizializza session_state per congelamento cards
        if 'cards_data' not in st.session_state:
            st.session_state.cards_data = None
        if 'dettagli_data' not in st.session_state:
            st.session_state.dettagli_data = None    
        if 'cards_filters' not in st.session_state:
            st.session_state.cards_filters = None
        if 'cards_frozen' not in st.session_state:
            st.session_state.cards_frozen = False
        
        # Funzione callback per congelare/scongelare
        def toggle_freeze():
            if not st.session_state.cards_frozen:
                # Congela: carica e salva ENTRAMBI i dati
                db = init_database()
                
                # Salva summary cards
                fresh_data = db.get_summary_cards(
                    date_from=filters['date_from'],
                    date_to=filters['date_to'],
                    exclude_obsolete=filters['exclude_obsolete'],
                    exclude_attribute_18=filters['exclude_attribute_18'],
                    magazzini=filters['magazzini'],
                    categorie=filters['categorie'],
                    marche=filters['marche'],
                    articoli_include=filters['articoli_include'],
                    articoli_exclude=filters['articoli_exclude'],
                    clienti_include=filters['clienti_include'],
                    clienti_exclude=filters['clienti_exclude']
                )
                st.session_state.cards_data = fresh_data
                
                # NUOVO: Salva anche dettaglio articoli
                dettagli_data = db.get_dettaglio_articoli(
                    date_from=filters['date_from'],
                    date_to=filters['date_to'],
                    exclude_obsolete=filters['exclude_obsolete'],
                    exclude_attribute_18=filters['exclude_attribute_18'],
                    magazzini=filters['magazzini'],
                    categorie=filters['categorie'],
                    marche=filters['marche'],
                    articoli_include=filters['articoli_include'],
                    articoli_exclude=filters['articoli_exclude'],
                    clienti_include=filters['clienti_include'],
                    clienti_exclude=filters['clienti_exclude']
                )
                st.session_state.dettagli_data = dettagli_data
                
                st.session_state.cards_filters = filters.copy()
            else:
                # Scongela: reset ENTRAMBI
                st.session_state.cards_data = None
                st.session_state.dettagli_data = None  # NUOVO
                st.session_state.cards_filters = None
            
            st.session_state.cards_frozen = not st.session_state.cards_frozen
        
        # Pulsante congela/scongela
        button_text = "💧 Scongela Dati" if st.session_state.cards_frozen else "❄️ Congela Dati"
        st.button(button_text, on_click=toggle_freeze, key="cards_freeze_btn")
        
        # Determina quali dati usare
        if st.session_state.cards_frozen and st.session_state.cards_data is not None:
            summary_data = st.session_state.cards_data
            frozen_filters = st.session_state.cards_filters
            
            # Expander con filtri congelati
            with st.expander("Dati congelati - Riepilogo filtri", expanded=False):
                st.write("**Periodo:** ", f"{frozen_filters.get('date_from')} - {frozen_filters.get('date_to')}")
                
                if frozen_filters.get('magazzini'):
                    st.write("**Magazzini:** ", ', '.join(frozen_filters['magazzini']))
                
                if frozen_filters.get('categorie'):
                    db = init_database()
                    categorie_df = db.get_categorie_list()
                    categorie_desc = []
                    for cod_cat in frozen_filters['categorie']:
                        match = categorie_df[categorie_df['Cd_ARGruppo1'] == cod_cat]
                        categorie_desc.append(match.iloc[0]['Descrizione'] if not match.empty else cod_cat)
                    st.write("**Categorie:** ", ', '.join(categorie_desc))
                
                if frozen_filters.get('marche'):
                    db = init_database()
                    marche_df = db.get_marche_list()
                    marche_desc = []
                    for cod_marca in frozen_filters['marche']:
                        match = marche_df[marche_df['Cd_ARMarca'] == cod_marca]
                        marche_desc.append(match.iloc[0]['Descrizione'] if not match.empty else cod_marca)
                    st.write("**Marche:** ", ', '.join(marche_desc))
                
                if frozen_filters.get('articoli_include'):
                    st.write("**Articoli inclusi:** ", f"{len(frozen_filters['articoli_include'])} selezionati")
                
                if frozen_filters.get('articoli_exclude'):
                    st.write("**Articoli esclusi:** ", f"{len(frozen_filters['articoli_exclude'])} selezionati")
                
                if frozen_filters.get('clienti_include'):
                    st.write("**Clienti inclusi:** ", f"{len(frozen_filters['clienti_include'])} selezionati")
                
                if frozen_filters.get('clienti_exclude'):
                    st.write("**Clienti esclusi:** ", f"{len(frozen_filters['clienti_exclude'])} selezionati")
                
                st.write("**Esclude obsoleti:** ", "Sì" if frozen_filters.get('exclude_obsolete') else "No")
                st.write("**Esclude attributo 18:** ", "Sì" if frozen_filters.get('exclude_attribute_18') else "No")
        else:
            # Dati freschi
            db = init_database()
            summary_data = db.get_summary_cards(
                date_from=filters['date_from'],
                date_to=filters['date_to'],
                exclude_obsolete=filters['exclude_obsolete'],
                exclude_attribute_18=filters['exclude_attribute_18'],
                magazzini=filters['magazzini'],
                categorie=filters['categorie'],
                marche=filters['marche'],
                articoli_include=filters['articoli_include'],
                articoli_exclude=filters['articoli_exclude'],
                clienti_include=filters['clienti_include'],
                clienti_exclude=filters['clienti_exclude']
            )
        
        # Mostra cards
        show_cards(summary_data)

        # NUOVO: Determina quali dati usare per DETTAGLIO ARTICOLI
        if st.session_state.cards_frozen and st.session_state.dettagli_data is not None:
            # Usa dati congelati
            dettagli_df = st.session_state.dettagli_data
        else:
            # Carica dati freschi
            db = init_database()
            dettagli_df = db.get_dettaglio_articoli(
                date_from=filters['date_from'],
                date_to=filters['date_to'],
                exclude_obsolete=filters['exclude_obsolete'],
                exclude_attribute_18=filters['exclude_attribute_18'],
                magazzini=filters['magazzini'],
                categorie=filters['categorie'],
                marche=filters['marche'],
                articoli_include=filters['articoli_include'],
                articoli_exclude=filters['articoli_exclude'],
                clienti_include=filters['clienti_include'],
                clienti_exclude=filters['clienti_exclude']
            )
        
        # Inizializza stato expander
        if 'dettaglio_expander_open' not in st.session_state:
            st.session_state.dettaglio_expander_open = False
        
        if not dettagli_df.empty:
            # Mostra help solo se ci sono più righe degli articoli totali
            show_help = False
            if not summary_data.empty:
                articoli_totali = int(summary_data.iloc[0]['Articoli_Totali'])
                if len(dettagli_df) > articoli_totali:
                    show_help = True
            
            help_text = (
                "ℹ️ Questa tabella contiene più righe rispetto al conteggio 'Articoli Totali' delle cards. "
                "Le righe aggiuntive sono articoli presenti solo in Note di Credito (NCC) emesse nel periodo selezionato, "
                "ma che non hanno avuto vendite. Si tratta di articoli rimborsati ai clienti "
                "senza essere stati venduti nel range di date selezionato."
            ) if show_help else None
            
            if st.session_state.dettaglio_expander_open:
                st.subheader(f"📋 Dettaglio Articoli ({len(dettagli_df)} righe)")

                if '::auto_unique_id::' in dettagli_df.columns:
                    dettagli_df = dettagli_df.drop(columns=['::auto_unique_id::'])

                gb_det = GridOptionsBuilder.from_dataframe(dettagli_df)
                gb_det.configure_default_column(filterable=True, sortable=True, resizable=True, editable=False)
                gb_det.configure_grid_options(domLayout='normal', rowHeight=40)
                gb_det.configure_side_bar(filters_panel=True, columns_panel=True)

                # Colonne nascoste (rimpiazza column_config=None del vecchio st.dataframe)
                gb_det.configure_column("MarginePercentuale", hide=True)
                gb_det.configure_column("Note", hide=True)

                AgGrid(
                    dettagli_df,
                    gridOptions=gb_det.build(),
                    height=500,
                    theme='alpine',
                    custom_css=AGGRID_CUSTOM_CSS,
                    allow_unsafe_jscode=True,
                    key='grid_dettaglio_articoli'
                )
            else:
                if st.button(
                    f"📋 Apri Dettaglio Articoli ({len(dettagli_df)} righe)",
                    key="toggle_dettaglio_btn",
                    help=help_text
                ):
                    st.session_state.dettaglio_expander_open = True
                    st.rerun()

    def show_cards(summary_data):
        """Funzione separata per mostrare le cards"""
        if summary_data is None or summary_data.empty:
            st.warning("Nessun dato trovato per i filtri selezionati")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Articoli Totali", 0)
            with col2:
                st.metric("Valore Totale", "€ 0,00")
            with col3:
                st.metric("Valore Totale Netto", "€ 0,00")
            with col4:
                st.metric("Margine Medio", "0.0%")
            return
        
        # Cards con dati
        row = summary_data.iloc[0]
        total_articles = int(row['Articoli_Totali'])
        total_value = float(row['Valore_Totale']) if row['Valore_Totale'] else 0.0
        total_value_net = float(row['Valore_Netto']) if row['Valore_Netto'] else 0.0
        avg_margin = float(row['Margine_Percentuale']) if row['Margine_Percentuale'] else 0.0
        
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Articoli Totali", 
                value= total_articles,
            )

        with col2:
            st.metric("Valore Totale", f"€ {total_value:,.2f}")

        with col3:
            st.metric(
                label="Valore Totale Netto",
                value=f"€ {total_value_net:,.2f}",
                help="Per calcolare il Valore Totale Netto vengono sottratti gli importi delle Note di Accredito al Cliente dal Valore Totale"
            )
        with col4:
            st.metric(
                label="Margine Medio",
                value=f"{avg_margin:.1f}%",
                help="Il Margine Medio viene calcolato sul Valore Totale"
            )

    def export_to_excel(df):
        """Esporta i dati in Excel"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Analisi_Magazzino', index=False)
            
            # Formatta il foglio
            workbook = writer.book
            worksheet = writer.sheets['Analisi_Magazzino']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return output.getvalue()

    def create_article_client_analysis(filters, user_role):
            """
            Crea tabella articoli con dettaglio clienti espandibile usando AgGrid Master-Detail
            """
            st.header("📋 Analisi Vendite: Articoli e Clienti")
            
            if st.button("🔄 Carica Analisi Articoli-Clienti", type="primary", key="load_analysis_btn"):
                with st.spinner("Caricamento dati in corso..."):
                    db = init_database()
                    articles_df = db.get_articles_sales_summary(
                        date_from=filters['date_from'],
                        date_to=filters['date_to'],
                        exclude_obsolete=filters['exclude_obsolete'],
                        exclude_attribute_18=filters['exclude_attribute_18'],
                        magazzini=filters['magazzini'],
                        categorie=filters['categorie'],
                        marche=filters['marche'],
                        articoli_include=filters['articoli_include'],
                        articoli_exclude=filters['articoli_exclude'],
                        clienti_include=filters['clienti_include'],
                        clienti_exclude=filters['clienti_exclude']
                    )
                    
                    if not articles_df.empty:
                        st.session_state['articles_analysis_data'] = articles_df
                        st.session_state['articles_analysis_filters'] = filters.copy()
                        if 'selected_article_row' in st.session_state:
                            del st.session_state['selected_article_row']
                        if 'selected_client_row' in st.session_state:
                            del st.session_state['selected_client_row']
                        st.success(f"✅ Caricati {len(articles_df)} articoli")
                        st.rerun()
                    else:
                        st.warning("⚠️ Nessun articolo trovato con i filtri selezionati")
                        return
                    
            if 'articles_analysis_data' not in st.session_state:
                st.info("👆 Clicca il pulsante sopra per caricare i dati")
                return
            
            articles_df = st.session_state['articles_analysis_data']
            stored_filters = st.session_state['articles_analysis_filters']
            
            st.caption(f"📅 Periodo: {stored_filters['date_from']} → {stored_filters['date_to']}")
            
            # ========================================
            # GRIGLIA ARTICOLI
            # ========================================
            display_df = articles_df.copy()
            
            column_names_map = {
                "Codice_Articolo": "Codice",
                "Descrizione": "Descrizione",
                "Categoria": "Categoria",
                "Marca": "Marca",
                "Totale_Qta_Venduta_PZ": "Qta PZ",
                "Totale_Qta_Venduta_CF": "Qta CF",
                "Totale_Valore_Venduto": "Valore €",
                "Num_Clienti_Distinti": "N° Clienti",
                "Giacenza_MG00002_CF": "Giacenza CF"
            }
            
            display_df = display_df.rename(columns=column_names_map)
            
            if user_role == 'acquisti':
                visible_columns = ["Codice", "Descrizione", "Categoria", "Marca", "Qta CF", "Giacenza CF"]
            else:
                visible_columns = list(column_names_map.values())
            
            display_df = display_df[visible_columns]

            if '::auto_unique_id::' in display_df.columns:
                display_df = display_df.drop(columns=['::auto_unique_id::'])
            
            st.subheader(f"📦 Articoli Venduti ({len(display_df)} risultati)")
            st.info("💡 Clicca su una riga per vedere i clienti che hanno acquistato l'articolo")
            
            gb = GridOptionsBuilder.from_dataframe(display_df)
            gb.configure_selection(selection_mode='single', use_checkbox=False, pre_selected_rows=[])
            gb.configure_side_bar(filters_panel=True, columns_panel=True)

            gb.configure_column("Codice", pinned="left", width=120, filter="agTextColumnFilter")
            gb.configure_column("Descrizione", width=300, filter="agTextColumnFilter")
            gb.configure_column("Categoria", width=150, filter="agSetColumnFilter")
            gb.configure_column("Marca", width=150, filter="agSetColumnFilter")

            if "Qta PZ" in visible_columns:
                gb.configure_column("Qta PZ", width=100, precision=0, type=["numberColumnFilter", "numericColumn"])

            if "Qta CF" in visible_columns:
                gb.configure_column("Qta CF", type=["numericColumn", "numberColumnFilter"], precision=2, width=100)

            if "Valore €" in visible_columns:
                gb.configure_column("Valore €", type=["numericColumn", "numberColumnFilter"], precision=2, width=120)

            if "N° Clienti" in visible_columns:
                gb.configure_column("N° Clienti", type=["numericColumn", "numberColumnFilter"], precision=0, width=110)

            if "Giacenza CF" in visible_columns:
                giacenza_formatter = JsCode("""
                    function(params) {
                        if (params.value == null || params.value === '') {
                            return 'Selezionare Magazzino';
                        }
                        return params.value.toLocaleString('it-IT', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                    }
                """)
                gb.configure_column(
                    "Giacenza CF",
                    type=["numericColumn", "numberColumnFilter"],
                    valueFormatter=giacenza_formatter,
                    precision=2,
                    width=120
                )
            
            gb.configure_default_column(filterable=True, sortable=True, resizable=True, editable=False)
            gb.configure_grid_options(domLayout='normal', rowHeight=40, enableRangeSelection=True, suppressRowDeselection=False)
            
            grid_response = AgGrid(
                display_df,
                gridOptions=gb.build(),
                height=450,
                allow_unsafe_jscode=True,
                theme='alpine',
                key='grid_articles',
                custom_css=AGGRID_CUSTOM_CSS
            )
            
            # ========================================
            # GRIGLIA CLIENTI
            # ========================================
            selected_rows = grid_response['selected_rows']
            
            if selected_rows is not None and len(selected_rows) > 0:
                selected_article = selected_rows.iloc[0]
                selected_code = selected_article['Codice']
                selected_desc = selected_article['Descrizione']
                
                st.divider()
                st.subheader(f"👥 Clienti che hanno acquistato: {selected_code} - {selected_desc}")
                
                with st.spinner(f"Caricamento clienti per {selected_code}..."):
                    db = init_database()
                    clients_df = db.get_clients_by_article(
                        cd_ar=selected_code,
                        date_from=stored_filters['date_from'],
                        date_to=stored_filters['date_to'],
                        exclude_obsolete=stored_filters['exclude_obsolete'],
                        exclude_attribute_18=stored_filters['exclude_attribute_18'],
                        magazzini=stored_filters['magazzini'],
                        categorie=stored_filters['categorie'],
                        marche=stored_filters['marche'],
                        articoli_include=stored_filters['articoli_include'],
                        articoli_exclude=stored_filters['articoli_exclude'],
                        clienti_include=stored_filters['clienti_include'],
                        clienti_exclude=stored_filters['clienti_exclude']
                    )
                
                if not clients_df.empty:
                    clients_display = clients_df.copy()
                    client_columns_map = {
                        "Codice_Cliente": "Cod. Cliente",
                        "Ragione_Sociale": "Ragione Sociale",
                        "Qta_Venduta_PZ": "Qta PZ",
                        "Qta_Venduta_CF": "Qta CF",
                        "Valore_Venduto": "Valore €",
                        "Num_Documenti": "N° Doc",
                        "Prima_Vendita": "Prima Vendita",
                        "Ultima_Vendita": "Ultima Vendita"
                    }
                    clients_display = clients_display.rename(columns=client_columns_map)
                    
                    if user_role == 'acquisti':
                        client_visible = ["Cod. Cliente", "Ragione Sociale", "Qta CF", "Prima Vendita", "Ultima Vendita"]
                    else:
                        client_visible = list(client_columns_map.values())
                    
                    clients_display = clients_display[client_visible]

                    if '::auto_unique_id::' in clients_display.columns:
                        clients_display = clients_display.drop(columns=['::auto_unique_id::'])
                    
                    gb_clients = GridOptionsBuilder.from_dataframe(clients_display)
                    
                    if user_role in ['admin', 'manager', 'logistica']:
                        gb_clients.configure_selection(selection_mode='single', use_checkbox=False, pre_selected_rows=[])
                    
                    gb_clients.configure_side_bar(filters_panel=True, columns_panel=True)
                    gb_clients.configure_column("Cod. Cliente", pinned="left", width=120, filter="agTextColumnFilter")
                    gb_clients.configure_column("Ragione Sociale", width=300, filter="agTextColumnFilter")

                    if "Qta PZ" in client_visible:
                        gb_clients.configure_column("Qta PZ", type=["numericColumn", "numberColumnFilter"], precision=0, width=100)

                    if "Qta CF" in client_visible:
                        gb_clients.configure_column("Qta CF", type=["numericColumn", "numberColumnFilter"], precision=2, width=100)

                    if "Valore €" in client_visible:
                        gb_clients.configure_column("Valore €", type=["numericColumn", "numberColumnFilter"], precision=2, width=120)

                    if "N° Doc" in client_visible:
                        gb_clients.configure_column("N° Doc", type=["numericColumn", "numberColumnFilter"], precision=0, width=90)

                    gb_clients.configure_column(
                        "Prima Vendita", width=130, filter="agDateColumnFilter",
                        valueFormatter=JsCode("""
                            function(params) {
                                if (!params.value) return '';
                                var d = new Date(params.value);
                                return d.toLocaleDateString('it-IT');
                            }
                        """)
                    )
                    gb_clients.configure_column(
                        "Ultima Vendita", width=130, filter="agDateColumnFilter",
                        valueFormatter=JsCode("""
                            function(params) {
                                if (!params.value) return '';
                                var d = new Date(params.value);
                                return d.toLocaleDateString('it-IT');
                            }
                        """)
                    )
                    
                    gb_clients.configure_default_column(filterable=True, sortable=True, resizable=True)
                    gb_clients.configure_grid_options(domLayout='normal', rowHeight=35)
                    
                    if user_role in ['admin', 'manager', 'logistica']:
                        st.info("💡 Clicca su un cliente per vedere i documenti")
                    
                    grid_clients_response = AgGrid(
                        clients_display,
                        gridOptions=gb_clients.build(),
                        height=350,
                        allow_unsafe_jscode=True,
                        theme='alpine',
                        key='grid_clients',
                        custom_css=AGGRID_CUSTOM_CSS
                    )

                    # ========================================
                    # GRIGLIA DOCUMENTI (solo admin/manager)
                    # ========================================
                    if user_role in ['admin', 'manager', 'logistica']:
                        selected_clients = grid_clients_response['selected_rows']
                        
                        if selected_clients is not None and len(selected_clients) > 0:
                            selected_client_row = selected_clients.iloc[0]
                            selected_client_code_display = selected_client_row['Cod. Cliente']
                            selected_client_name = selected_client_row['Ragione Sociale']
                            
                            matching_row = clients_df[clients_df['Codice_Cliente'] == selected_client_code_display]
                            
                            if not matching_row.empty:
                                selected_client_code = matching_row.iloc[0]['Codice_Cliente']
                                
                                st.divider()
                                st.subheader(f"📄 Documenti: {selected_client_code} - {selected_client_name}")
                                
                                with st.spinner("Caricamento documenti..."):
                                    db = init_database()
                                    docs_df = db.get_documents_by_article_client(
                                        cd_ar=selected_code,
                                        cd_cf=selected_client_code,
                                        date_from=stored_filters['date_from'],
                                        date_to=stored_filters['date_to']
                                    )
                                
                                if not docs_df.empty:
                                    if '::auto_unique_id::' in docs_df.columns:
                                        docs_df = docs_df.drop(columns=['::auto_unique_id::'])

                                    gb_docs = GridOptionsBuilder.from_dataframe(docs_df)
                                    gb_docs.configure_side_bar(filters_panel=True, columns_panel=True)
                                    gb_docs.configure_column("Tipo_Documento", header_name="Tipo", width=100, filter="agTextColumnFilter")
                                    gb_docs.configure_column("Numero_Documento", header_name="Numero Documento", width=180, filter="agTextColumnFilter")
                                    gb_docs.configure_column(
                                        "Data_Documento", header_name="Data", width=130,
                                        filter="agDateColumnFilter",
                                        valueFormatter=JsCode("""
                                            function(params) {
                                                if (!params.value) return '';
                                                var d = new Date(params.value);
                                                return d.toLocaleDateString('it-IT');
                                            }
                                        """)
                                    )
                                    gb_docs.configure_column("Valore", header_name="Valore €", type=["numericColumn", "numberColumnFilter"], precision=2, width=130)
                                    gb_docs.configure_default_column(filterable=True, sortable=True, resizable=True)
                                    gb_docs.configure_grid_options(domLayout='normal', rowHeight=45)
                                    
                                    AgGrid(
                                        docs_df,
                                        gridOptions=gb_docs.build(),
                                        height=300,
                                        allow_unsafe_jscode=True,
                                        theme='alpine',
                                        key=f'grid_docs_{selected_client_code}',
                                        custom_css=AGGRID_CUSTOM_CSS
                                    )
                                else:
                                    st.info("Nessun documento trovato")
                            else:
                                st.error(f"❌ Errore: cliente {selected_client_code_display} non trovato")

                            # ========================================
                            # EXPORT EXCEL
                            # ========================================
                            if has_permission('export_data'):
                                st.divider()
                                col_exp1, col_exp2 = st.columns(2)
                                
                                with col_exp1:
                                    excel_data = export_to_excel(articles_df)
                                    st.download_button(
                                        label="📥 Download Excel Articoli",
                                        data=excel_data,
                                        file_name=f"analisi_articoli_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_articles_main"
                                    )
                                
                                if selected_rows is not None and len(selected_rows) > 0:
                                    selected_code = selected_rows.iloc[0]['Codice']
                                    db = init_database()
                                    clients_df_export = db.get_clients_by_article(
                                        cd_ar=selected_code,
                                        date_from=stored_filters['date_from'],
                                        date_to=stored_filters['date_to'],
                                        exclude_obsolete=stored_filters['exclude_obsolete'],
                                        exclude_attribute_18=stored_filters['exclude_attribute_18'],
                                        magazzini=stored_filters['magazzini'],
                                        categorie=stored_filters['categorie'],
                                        marche=stored_filters['marche'],
                                        articoli_include=stored_filters['articoli_include'],
                                        articoli_exclude=stored_filters['articoli_exclude'],
                                        clienti_include=stored_filters['clienti_include'],
                                        clienti_exclude=stored_filters['clienti_exclude']
                                    )
                                    
                                    if not clients_df_export.empty:
                                        with col_exp2:
                                            excel_clients = export_to_excel(clients_df_export)
                                            st.download_button(
                                                label=f"📥 Download Clienti ({selected_code})",
                                                data=excel_clients,
                                                file_name=f"clienti_{selected_code}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key="download_clients_detail"
                                            )
# ========================================
# FUNZIONE MAIN MODIFICATA CON PERMESSI
# ========================================

    # ========================================
    # MAIN CON PERMESSI
    # ========================================
    
    def main():
        st.title("📦 Analisi Magazzino")
        
        # Crea filtri
        filters = create_filters()
        
        # SEZIONE CARDS
        if has_permission('view_cards'):
            st.header("📊 Riepilogo Generale - Cards")
            create_summary_cards(filters)
        # else:
        #     st.warning("⚠️ Non hai i permessi per visualizzare le cards")
        
        # SEZIONE GRAFICI
        if has_permission('view_charts'):
            st.divider()
            st.header("📊 Grafici Analitici")
            
            col_chart1, col_divider, col_chart2 = st.columns([5, 1, 5])
            
            with col_chart1:
                st.subheader("🏆 Top Articoli")
                create_top_articles_chart(filters)
            
            with col_divider:
                st.markdown("""
                    <div style="
                        height: 800px; 
                        border-left: 2px solid #e0e0e0; 
                        margin: 20px 0;
                    ">
                    </div>
                """, unsafe_allow_html=True)
            
            with col_chart2:
                st.subheader("🏆 Top Clienti")
                create_top_clients_chart(filters)
        # else:
        #     st.warning("⚠️ Non hai i permessi per visualizzare i grafici")
        
        # ANALISI MENSILE
        if has_permission('view_monthly'):
            st.divider()
            st.header("Analisi Mensile per Anno")
            
            col_year1, col_year2 = st.columns([1, 3])
            with col_year1:
                selected_year = st.selectbox(
                    "Seleziona Anno:",
                    options=[2026, 2025, 2024, 2023, 2022, 2021, 2020],
                    index=0,
                    key="year_filter"
                )
            
            with col_year2:
                if st.button("Carica Analisi Mensile", type="secondary"):
                    with st.spinner("Caricamento breakdown mensile..."):
                        db = init_database()
                        monthly_df = db.get_monthly_breakdown(
                            year=selected_year,
                            exclude_obsolete=filters['exclude_obsolete'],
                            exclude_attribute_18=filters['exclude_attribute_18'],
                            magazzini=filters['magazzini'],
                            categorie=filters['categorie'],
                            marche=filters['marche'],
                            articoli_include=filters['articoli_include'],
                            articoli_exclude=filters['articoli_exclude'],
                            clienti_include=filters['clienti_include'],
                            clienti_exclude=filters['clienti_exclude']
                        )
                        
                        if not monthly_df.empty:
                            st.session_state['monthly_data'] = monthly_df
                            st.session_state['monthly_year_used'] = selected_year
            
            # Mostra tabella mensile
            if 'monthly_data' in st.session_state and not st.session_state['monthly_data'].empty:
                monthly_df = st.session_state['monthly_data']
                used_year = st.session_state.get('monthly_year_used', selected_year)
                
                st.info(f"📊 Breakdown mensile: {len(monthly_df)} articoli per l'anno {used_year}")
                st.subheader(f"Vendite Mensili in Confezioni (CF) - Anno {used_year}")

                if '::auto_unique_id::' in monthly_df.columns:
                    monthly_df = monthly_df.drop(columns=['::auto_unique_id::'])

                gb_monthly = GridOptionsBuilder.from_dataframe(monthly_df)
                gb_monthly.configure_default_column(filterable=True, sortable=True, resizable=True)
                gb_monthly.configure_grid_options(domLayout='normal', rowHeight=45)
                gb_monthly.configure_side_bar(filters_panel=True, columns_panel=True)

                AgGrid(
                    monthly_df,
                    gridOptions=gb_monthly.build(),
                    height=500,
                    theme='alpine',
                    custom_css=AGGRID_CUSTOM_CSS,
                    allow_unsafe_jscode=True,
                    key=f'grid_monthly_{used_year}'
                )
                        
        # PIANIFICAZIONE ORDINI
        if has_permission('view_orders'):
            st.divider()
            st.header("📋 Pianificazione Ordini")
            
            col_months1, col_months2 = st.columns([1, 3])
            with col_months1:
                target_months = st.number_input(
                    "Mesi di copertura desiderati:",
                    min_value=0.5,
                    max_value=24.0,
                    value=3.0,
                    step=0.5,
                    key="target_months"
                )
            
            with col_months2:
                if st.button("Calcola Ordini", type="secondary"):
                    with st.spinner("Calcolo pianificazione ordini..."):
                        db = init_database()
                        order_df = db.get_order_planning(
                            date_from=filters['date_from'],
                            date_to=filters['date_to'],
                            target_months=target_months,
                            exclude_obsolete=filters['exclude_obsolete'],
                            exclude_attribute_18=filters['exclude_attribute_18'],
                            magazzini=filters['magazzini'],
                            categorie=filters['categorie'],
                            marche=filters['marche'],
                            articoli_include=filters['articoli_include'],
                            articoli_exclude=filters['articoli_exclude'],
                            clienti_include=filters['clienti_include'],
                            clienti_exclude=filters['clienti_exclude']
                        )
                        
                        if not order_df.empty:
                            st.session_state['order_data'] = order_df
                            st.session_state['order_months_used'] = target_months
            
            # Mostra tabella ordini
            if 'order_data' in st.session_state and not st.session_state['order_data'].empty:
                order_df = st.session_state['order_data']
                used_months = st.session_state.get('order_months_used', target_months)
                
                st.info(f"📋 Trovati {len(order_df)} articoli per {used_months} mesi di copertura")
                st.subheader(f"Articoli da Ordinare - Copertura {used_months} Mesi")

                if '::auto_unique_id::' in order_df.columns:
                    order_df = order_df.drop(columns=['::auto_unique_id::'])

                gb_order = GridOptionsBuilder.from_dataframe(order_df)
                gb_order.configure_default_column(filterable=True, sortable=True, resizable=True, editable=False)
                gb_order.configure_grid_options(domLayout='normal', rowHeight=40)
                gb_order.configure_side_bar(filters_panel=True, columns_panel=True)

                gb_order.configure_column("Codice", pinned="left", width=120, filter="agTextColumnFilter")
                gb_order.configure_column("Descrizione_AR", filter="agTextColumnFilter")

                # Colonne nascoste di default
                gb_order.configure_column("Qta_da_Ordinare_CA", hide=True)
                gb_order.configure_column("Qta_da_Ordinare_PZ_Base", hide=True)
                gb_order.configure_column("PZ x CA", hide=True)
                gb_order.configure_column("PZ x PL", hide=True)
                gb_order.configure_column("Mesi_Coperti", hide=True)
                gb_order.configure_column("Venduto_Periodo_CF", hide=True)
                gb_order.configure_column("UltCost_(PZ)", hide=True)
                gb_order.configure_column("Prz_B2B_(PZ)", hide=True)
                gb_order.configure_column(
                    "Scadenza",
                    hide=False,
                    filter="agDateColumnFilter",
                    valueFormatter=JsCode("""
                        function(params) {
                            if (!params.value) return '';
                            var d = new Date(params.value);
                            return d.toLocaleDateString('it-IT');
                        }
                    """)
                )

                if "EAN_(PZ)" in order_df.columns:
                    gb_order.configure_column("EAN_(PZ)", type=["stringColumn"], width=160)

                if "Giacenza_Attuale_CF" in order_df.columns:
                    giacenza_formatter_order = JsCode("""
                        function(params) {
                            if (params.value == null || params.value === '') {
                                return 'Selezionare Magazzino';
                            }
                            return params.value.toLocaleString('it-IT', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    """)
                    gb_order.configure_column(
                        "Giacenza_Attuale_CF",
                        type=["numericColumn", "numberColumnFilter"],
                        valueFormatter=giacenza_formatter_order,
                        precision=2
                    )

                AgGrid(
                    order_df,
                    gridOptions=gb_order.build(),
                    height=500,
                    theme='alpine',
                    custom_css=AGGRID_CUSTOM_CSS,
                    allow_unsafe_jscode=True,
                    key=f'grid_orders_{used_months}'
                )
    
        # ANALISI ARTICOLI-CLIENTI
        if has_permission('view_article_client_analysis'):
            st.divider()
            create_article_client_analysis(filters, user_role)

    # ========================================
    # ESECUZIONE MAIN
    # ========================================
    if __name__ == "__main__":
        main()

elif st.session_state.get("authentication_status") == False:
    st.error('❌ Username o password non corretti')
    st.stop()
elif st.session_state.get("authentication_status") == None:
    st.warning('⚠️ Inserisci username e password per accedere')
    st.stop()