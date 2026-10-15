import pandas as pd
from sqlalchemy import text
from config import DatabaseConfig
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = self.config.get_engine()
    
    def execute_query(self, query, params=None):
        """Esegue una query e restituisce un DataFrame"""
        try:
            with self.engine.connect() as conn:
                result = pd.read_sql(text(query), conn, params=params)
            return result
        except Exception as e:
            print(f"Errore nell'esecuzione della query: {e}")
            return pd.DataFrame()

    def get_magazzini_list(self):
        """Ottiene la lista dei magazzini"""
        try:
            query = "SELECT DISTINCT Cd_MG, Descrizione FROM MG ORDER BY Cd_MG"
            return self.execute_query(query)
        except:
            return pd.DataFrame({'Cd_MG': [], 'Descrizione': []})
    
    def get_categorie_list(self, selected_marche=None):
        """Ottiene categorie, filtrate per marche se specificate (include obsoleti)"""
        try:
            query = """
            SELECT DISTINCT
                ARGruppo1.Cd_ARGruppo1,
                ARGruppo1.Descrizione
            FROM ARGruppo1
            """
            
            params = {}
            
            if selected_marche and len(selected_marche) > 0:
                query += """
                INNER JOIN AR ON AR.Cd_ARGruppo1 = ARGruppo1.Cd_ARGruppo1
                WHERE 1=1
                """
                placeholders = ','.join([f':marca_{i}' for i in range(len(selected_marche))])
                query += f" AND AR.Cd_ARMarca IN ({placeholders})"
                for i, marca in enumerate(selected_marche):
                    params[f'marca_{i}'] = marca
            
            query += " ORDER BY ARGruppo1.Descrizione"
            return self.execute_query(query, params)
        except:
            return pd.DataFrame({'Cd_ARGruppo1': [], 'Descrizione': []})
    
    def get_articoli_list(self, selected_categories=None, selected_marche=None):
        """Ottiene articoli filtrati per categorie E marche (include obsoleti)"""
        try:
            query = """
            SELECT 
                AR.Cd_AR, 
                AR.Descrizione,
                CONCAT(AR.Cd_AR, ' - ', AR.Descrizione) AS Display_Text
            FROM AR 
            WHERE 1=1
            """
            
            params = {}
            
            # Filtro categorie
            if selected_categories and len(selected_categories) > 0:
                placeholders = ','.join([f':cat_{i}' for i in range(len(selected_categories))])
                query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
                for i, cat in enumerate(selected_categories):
                    params[f'cat_{i}'] = cat
            
            # Filtro marche
            if selected_marche and len(selected_marche) > 0:
                placeholders = ','.join([f':marca_{i}' for i in range(len(selected_marche))])
                query += f" AND AR.Cd_ARMarca IN ({placeholders})"
                for i, marca in enumerate(selected_marche):
                    params[f'marca_{i}'] = marca
            
            query += " ORDER BY AR.Cd_AR"
            return self.execute_query(query, params)
        except:
            return pd.DataFrame({'Cd_AR': [], 'Descrizione': [], 'Display_Text': []})
    
    def get_clienti_list(self):
        """Ottiene la lista dei clienti con descrizione"""
        try:
            query = """
            SELECT 
                CF.Cd_CF, 
                CF.Descrizione,
                CONCAT(CF.Cd_CF, ' - ', CF.Descrizione) AS Display_Text
            FROM CF 
            WHERE CF.TipoCF LIKE '%C%' 
            ORDER BY CF.Descrizione
            """
            return self.execute_query(query)
        except:
            return pd.DataFrame({'Cd_CF': [], 'Descrizione': [], 'Display_Text': []})
    
    def get_marche_list(self, selected_categories=None):
        """Ottiene marche, filtrate per categorie se specificate (include obsoleti)"""
        try:
            query = """
            SELECT DISTINCT
                ARMarca.Cd_ARMarca,
                ARMarca.Descrizione
            FROM ARMarca
            """
            
            params = {}
            
            if selected_categories and len(selected_categories) > 0:
                query += """
                INNER JOIN AR ON AR.Cd_ARMarca = ARMarca.Cd_ARMarca
                WHERE 1=1
                """
                placeholders = ','.join([f':cat_{i}' for i in range(len(selected_categories))])
                query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
                for i, cat in enumerate(selected_categories):
                    params[f'cat_{i}'] = cat
            
            query += " ORDER BY ARMarca.Descrizione"
            return self.execute_query(query, params)
        except:
            return pd.DataFrame({'Cd_ARMarca': [], 'Descrizione': []})

    def search_marche(self, search_term, selected_categories=None):
        """Cerca marche per descrizione, filtrate per categorie se specificate"""
        try:
            query = """
            SELECT DISTINCT 
                ARMarca.Cd_ARMarca, 
                ARMarca.Descrizione 
            FROM ARMarca
            """
            
            params = {'search_term': f'%{search_term}%'}
            
            if selected_categories and len(selected_categories) > 0:
                query += """
                INNER JOIN AR ON AR.Cd_ARMarca = ARMarca.Cd_ARMarca
                WHERE ARMarca.Descrizione LIKE :search_term
                """
                placeholders = ','.join([f':cat_{i}' for i in range(len(selected_categories))])
                query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
                for i, cat in enumerate(selected_categories):
                    params[f'cat_{i}'] = cat
            else:
                query += " WHERE ARMarca.Descrizione LIKE :search_term"
            
            query += " ORDER BY ARMarca.Descrizione"
            
            return self.execute_query(query, params)
        except:
            return pd.DataFrame({'Cd_ARMarca': [], 'Descrizione': []})

    def search_articoli(self, search_term, selected_categories=None, selected_marche=None):
        """Cerca articoli filtrati per categorie E marche (include obsoleti)"""
        try:
            query = """
            SELECT
                AR.Cd_AR, 
                AR.Descrizione,
                CONCAT(AR.Cd_AR, ' - ', AR.Descrizione) AS Display_Text
            FROM AR 
            WHERE (AR.Cd_AR LIKE :search_term OR AR.Descrizione LIKE :search_term)
            """
            
            params = {'search_term': f'%{search_term}%'}
            
            # Filtro categorie
            if selected_categories and len(selected_categories) > 0:
                placeholders = ','.join([f':cat_{i}' for i in range(len(selected_categories))])
                query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
                for i, cat in enumerate(selected_categories):
                    params[f'cat_{i}'] = cat
            
            # Filtro marche
            if selected_marche and len(selected_marche) > 0:
                placeholders = ','.join([f':marca_{i}' for i in range(len(selected_marche))])
                query += f" AND AR.Cd_ARMarca IN ({placeholders})"
                for i, marca in enumerate(selected_marche):
                    params[f'marca_{i}'] = marca
            
            query += " ORDER BY AR.Cd_AR"
            return self.execute_query(query, params)
        except:
            return pd.DataFrame({'Cd_AR': [], 'Descrizione': [], 'Display_Text': []})
    
    def search_clienti(self, search_term):
        """Cerca clienti per codice o descrizione"""
        try:
            query = """
            SELECT TOP 50
                CF.Cd_CF, 
                CF.Descrizione,
                CONCAT(CF.Cd_CF, ' - ', CF.Descrizione) AS Display_Text
            FROM CF 
            WHERE CF.TipoCF LIKE '%C%' 
            AND (CF.Cd_CF LIKE :search_term OR CF.Descrizione LIKE :search_term)
            ORDER BY CF.Descrizione
            """
            params = {'search_term': f'%{search_term}%'}
            return self.execute_query(query, params)
        except:
            return pd.DataFrame({'Cd_CF': [], 'Descrizione': [], 'Display_Text': []})
        
    def get_magazzini_list_with_descriptions(self):
        """Ottiene la lista dei magazzini con descrizioni"""
        try:
            query = """
            SELECT 
                MG.Cd_MG, 
                MG.Descrizione,
                CONCAT(MG.Cd_MG, ' - ', MG.Descrizione) AS Display_Text
            FROM MG 
            ORDER BY MG.Cd_MG
            """
            return self.execute_query(query)
        except:
            return pd.DataFrame({'Cd_MG': [], 'Descrizione': [], 'Display_Text': []})

    def get_dettaglio_articoli(self, date_from, date_to, exclude_obsolete=True, exclude_attribute_18=True,
                            magazzini=None, categorie=None, marche=None, 
                            articoli_include=None, articoli_exclude=None,
                            clienti_include=None, clienti_exclude=None, **kwargs):
        """Query di dettaglio per singolo articolo con Valore Totale, Valore Netto e Margine"""

        query = """
        WITH MovimentiVendite AS (
            SELECT
                MGMov.Cd_AR,
                SUM(MGMov.Valore * MGMov.ScaV) AS ValoreTotale,
                SUM(MGMov.Quantita * MGMov.ScaV * ISNULL(CS.Costo,0)) AS CostoTotale
            FROM MGMov
                INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
                LEFT JOIN MGMovInt ON MGMov.Id_MGMovInt = MGMovInt.Id_MGMovInt
                LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
                LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
                LEFT JOIN CF CF_TAB ON CF_TAB.Cd_CF = DOTes.Cd_CF
                LEFT JOIN ARCostoItem CS ON CS.Cd_AR = MGMov.Cd_AR 
                    AND CS.TipoCosto = 'U'
                    AND CS.Cd_MGEsercizio = YEAR(GETDATE())
            WHERE MGMov.DataMov BETWEEN :date_from AND :date_to
        """

        params = {
            'date_from': date_from,
            'date_to': date_to
        }

        # Filtri condizionali (stessi di get_summary_cards)
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"

        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR
                    FROM AR AR_Filter
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """

        if magazzini and len(magazzini) > 0:
            placeholders = ",".join([f":mg_{i}" for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f"mg_{i}"] = mg

        if articoli_include and len(articoli_include) > 0:
            placeholders = ",".join([f":art_inc_{i}" for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f"art_inc_{i}"] = art

        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ",".join([f":art_exc_{i}" for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f"art_exc_{i}"] = art

        if categorie and len(categorie) > 0:
            placeholders = ",".join([f":cat_{i}" for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f"cat_{i}"] = cat

        if marche and len(marche) > 0:
            placeholders = ",".join([f":marca_{i}" for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f"marca_{i}"] = marca

        if clienti_include and len(clienti_include) > 0:
            placeholders = ",".join([f":cli_inc_{i}" for i in range(len(clienti_include))])
            query += f" AND CF_TAB.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f"cli_inc_{i}"] = cli

        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ",".join([f":cli_exc_{i}" for i in range(len(clienti_exclude))])
            query += f" AND (CF_TAB.Cd_CF NOT IN ({placeholders}) OR CF_TAB.Cd_CF IS NULL)"
            for i, cli in enumerate(clienti_exclude):
                params[f"cli_exc_{i}"] = cli

        query += """
            GROUP BY MGMov.Cd_AR
        ),
        NCCArticoli AS (
            SELECT
                R.Cd_AR,
                SUM(R.PrezzoTotaleV) AS ValoreNCC
            FROM DOTes T
            INNER JOIN DORig R ON R.Id_DOTes = T.Id_DOTes
            WHERE T.Cd_Do = 'NCC'
                AND T.DataDoc BETWEEN :date_from AND :date_to
                AND R.PrezzoTotaleV <> 0
                AND R.Cd_AR IS NOT NULL
            GROUP BY R.Cd_AR
        )
        SELECT
            V.Cd_AR,
            AR.Descrizione,
            ISNULL(V.ValoreTotale,0) AS ValoreTotale,
            ISNULL(V.ValoreTotale,0) - ISNULL(N.ValoreNCC,0) AS ValoreNetto,
            CASE WHEN ISNULL(V.ValoreTotale,0) = 0 THEN 0
                ELSE ((ISNULL(V.ValoreTotale,0) - ISNULL(V.CostoTotale,0)) / ISNULL(V.ValoreTotale,0)) * 100
            END AS MarginePercentuale,
            '' AS Note
        FROM MovimentiVendite V
        LEFT JOIN NCCArticoli N ON N.Cd_AR = V.Cd_AR
        INNER JOIN AR ON AR.Cd_AR = V.Cd_AR
        --WHERE ISNULL(V.ValoreTotale,0) <> 0

        UNION ALL
        
        -- Articoli con NCC ma senza movimenti di magazzino
        SELECT
            R.Cd_AR,
            AR_NCC.Descrizione,
            0 AS ValoreTotale,
            -SUM(R.PrezzoTotaleV) AS ValoreNetto,
            0 AS MarginePercentuale,
            'NCC senza movimenti nel periodo' AS Note  -- Spiegazione
        FROM DOTes T
        INNER JOIN DORig R ON R.Id_DOTes = T.Id_DOTes
        INNER JOIN AR AR_NCC ON AR_NCC.Cd_AR = R.Cd_AR
        WHERE T.Cd_Do = 'NCC'
            AND T.DataDoc BETWEEN :date_from AND :date_to
            AND R.PrezzoTotaleV <> 0
            AND R.Cd_AR IS NOT NULL
            AND R.Cd_AR NOT IN (SELECT DISTINCT Cd_AR FROM MovimentiVendite)
        GROUP BY R.Cd_AR, AR_NCC.Descrizione
        HAVING SUM(R.PrezzoTotaleV) <> 0
        
        ORDER BY Cd_AR
    """

        return self.execute_query(query, params)
    
    def get_summary_cards(self, date_from, date_to, exclude_obsolete=True, exclude_attribute_18=True,
                        magazzini=None, categorie=None, marche=None, 
                        articoli_include=None, articoli_exclude=None,
                        clienti_include=None, clienti_exclude=None, **kwargs):
        """Query leggera per cards di riepilogo - solo articoli con movimenti"""
        
        query = """
    WITH MovimentiConRMC AS (
        SELECT
            MGMov.Cd_AR,
            SUM(MGMov.Valore * MGMov.ScaV) AS ValoreV,
            SUM(MGMov.Quantita * MGMov.ScaV * ISNULL(CS.Costo, 0)) AS CostoV
        FROM MGMov
                INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
                LEFT JOIN MGMovInt ON MGMov.Id_MGMovInt = MGMovInt.Id_MGMovInt
                LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
                LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
                LEFT JOIN CF CF_TAB ON CF_TAB.Cd_CF = DOTes.Cd_CF
                LEFT JOIN ARCostoItem CS ON CS.Cd_AR = MGMov.Cd_AR 
                    AND CS.TipoCosto = 'U' 
                    AND CS.Cd_MGEsercizio = YEAR(GETDATE())
        WHERE 
            MGMov.DataMov >= :date_from
            AND MGMov.DataMov <= :date_to
        """
        
        # Aggiungi filtri condizionali
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR 
                    FROM AR AR_Filter 
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        params = {
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Filtri magazzini
        if magazzini and len(magazzini) > 0:
            placeholders = ','.join([f':mg_{i}' for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f'mg_{i}'] = mg

        # Filtri articoli - include
        if articoli_include and len(articoli_include) > 0:
            placeholders = ','.join([f':art_inc_{i}' for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f'art_inc_{i}'] = art

        # Filtri articoli - exclude
        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ','.join([f':art_exc_{i}' for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f'art_exc_{i}'] = art

        # Filtri categorie
        if categorie and len(categorie) > 0:
            placeholders = ','.join([f':cat_{i}' for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f'cat_{i}'] = cat

        # Filtri marche
        if marche and len(marche) > 0:
            placeholders = ','.join([f':marca_{i}' for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f'marca_{i}'] = marca

        # Filtri clienti - include (SOLO movimenti di quei clienti)
        if clienti_include and len(clienti_include) > 0:
            placeholders = ','.join([f':cli_inc_{i}' for i in range(len(clienti_include))])
            query += f" AND CF_TAB.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f'cli_inc_{i}'] = cli

        # Filtri clienti - exclude
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ','.join([f':cli_exc_{i}' for i in range(len(clienti_exclude))])
            query += f" AND (CF_TAB.Cd_CF NOT IN ({placeholders}) OR CF_TAB.Cd_CF IS NULL)"
            for i, cli in enumerate(clienti_exclude):
                params[f'cli_exc_{i}'] = cli

        query += """
        GROUP BY MGMov.Cd_AR
        ),
        NCCTotale AS (
            SELECT
                SUM(R.PrezzoTotaleV) AS ValoreNCC_Totale
            FROM DOTes T
            INNER JOIN DORig R ON R.Id_DOTes = T.Id_DOTes
            WHERE T.Cd_Do = 'NCC'
                AND T.DataDoc BETWEEN :date_from AND :date_to
                AND R.PrezzoTotaleV <> 0  -- Esclude valori zero
                AND R.Cd_AR IS NOT NULL
        )
        SELECT 
            COUNT(DISTINCT M.Cd_AR) as Articoli_Totali,
            SUM(M.ValoreV) as Valore_Totale,  -- 406.717,97
            SUM(M.ValoreV) - (SELECT ISNULL(ValoreNCC_Totale, 0) FROM NCCTotale) as Valore_Netto,  -- 403.195,27
            SUM(M.CostoV) as Costo_Totale,
            CASE WHEN SUM(M.ValoreV) = 0 THEN 0 
                ELSE ((SUM(M.ValoreV) - SUM(M.CostoV)) / SUM(M.ValoreV)) * 100 
            END as Margine_Percentuale
        FROM MovimentiConRMC M
        """

        return self.execute_query(query, params)

    def get_top_articles_chart(self, date_from, date_to, limit=20, exclude_obsolete=True, exclude_attribute_18=True,
                            magazzini=None, categorie=None, marche=None, 
                            articoli_include=None, articoli_exclude=None,
                            clienti_include=None, clienti_exclude=None, **kwargs):
        """Query per grafico Top 20 articoli per valore venduto"""
        
        query = """
        SELECT TOP (:limit)
            AR.Cd_AR AS Codice,
            AR.Descrizione AS Descrizione_AR,
            ISNULL(ARGruppo1.Descrizione, 'N/A') AS Categoria,
            ISNULL(ARMarca.Descrizione, 'N/A') AS Marca,
            SUM(MGMov.Valore * MGMov.ScaV) AS Valore_Totale,
            ROUND(SUM(MGMov.Quantita * MGMov.ScaV) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Quantita_CF,
            CONCAT(AR.Cd_AR, ' - ', LEFT(AR.Descrizione, 30)) AS Display_Label
        FROM MGMov
            INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
            LEFT JOIN ARGruppo1 ON AR.Cd_ARGruppo1 = ARGruppo1.Cd_ARGruppo1
            LEFT JOIN ARMarca ON AR.Cd_ARMarca = ARMarca.Cd_ARMarca
            LEFT JOIN ARARMisura CF ON CF.Cd_AR = AR.Cd_AR AND CF.Cd_ARMisura = 'CF'
            LEFT JOIN MGMovInt ON MGMov.Id_MGMovInt = MGMovInt.Id_MGMovInt
            LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
            LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
            LEFT JOIN CF CF_TAB ON CF_TAB.Cd_CF = DOTes.Cd_CF
        WHERE 
            MGMov.DataMov >= :date_from
            AND MGMov.DataMov <= :date_to
        """
        
        # Filtri condizionali
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR
                    FROM AR AR_Filter
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        params = {
            'date_from': date_from,
            'date_to': date_to,
            'limit': limit
        }
        
        # ✅ I TUOI FILTRI (perfetti per articoli)
        # Filtri magazzini
        if magazzini and len(magazzini) > 0:
            placeholders = ','.join([f':mg_{i}' for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f'mg_{i}'] = mg
                
        # Filtri articoli - include
        if articoli_include and len(articoli_include) > 0:
            placeholders = ','.join([f':art_inc_{i}' for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f'art_inc_{i}'] = art
                
        # Filtri articoli - exclude
        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ','.join([f':art_exc_{i}' for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f'art_exc_{i}'] = art
                
        # Filtri categorie
        if categorie and len(categorie) > 0:
            placeholders = ','.join([f':cat_{i}' for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f'cat_{i}'] = cat
                
        # Filtri marche
        if marche and len(marche) > 0:
            placeholders = ','.join([f':marca_{i}' for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f'marca_{i}'] = marca
        
        # Filtri clienti (per articoli: includere solo vendite a certi clienti)
        if clienti_include and len(clienti_include) > 0:
            placeholders = ','.join([f':cli_inc_{i}' for i in range(len(clienti_include))])
            query += f" AND CF_TAB.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f'cli_inc_{i}'] = cli
                
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ','.join([f':cli_exc_{i}' for i in range(len(clienti_exclude))])
            query += f" AND (CF_TAB.Cd_CF NOT IN ({placeholders}) OR CF_TAB.Cd_CF IS NULL)"
            for i, cli in enumerate(clienti_exclude):
                params[f'cli_exc_{i}'] = cli
        
        query += """
        GROUP BY AR.Cd_AR, AR.Descrizione, ARGruppo1.Descrizione, ARMarca.Descrizione, CF.UMFatt
        ORDER BY Valore_Totale DESC
        """
        
        return self.execute_query(query, params)

    def get_top_clients_chart(self, date_from, date_to, limit=20, exclude_obsolete=True, exclude_attribute_18=True,
                            magazzini=None, categorie=None, marche=None, 
                            articoli_include=None, articoli_exclude=None, 
                            clienti_include=None, clienti_exclude=None, **kwargs):
        """Query per grafico Top 20 clienti per valore venduto (NO filtro clienti)"""
        
        query = """
        SELECT TOP (:limit)
            CF_TAB.Cd_CF AS Codice_Cliente,
            CF_TAB.Descrizione AS Nome_Cliente,
            SUM(MGMov.Valore * MGMov.ScaV) AS Valore_Totale,
            COUNT(DISTINCT AR.Cd_AR) AS Num_Articoli_Diversi,
            CONCAT(CF_TAB.Cd_CF, ' - ', LEFT(CF_TAB.Descrizione, 25)) AS Display_Label
        FROM MGMov
            INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
            LEFT JOIN MGMovInt ON MGMov.Id_MGMovInt = MGMovInt.Id_MGMovInt
            LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
            LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
            INNER JOIN CF CF_TAB ON CF_TAB.Cd_CF = DOTes.Cd_CF
            LEFT JOIN ARGruppo1 ON AR.Cd_ARGruppo1 = ARGruppo1.Cd_ARGruppo1
            LEFT JOIN ARMarca ON AR.Cd_ARMarca = ARMarca.Cd_ARMarca
        WHERE 
            MGMov.DataMov >= :date_from
            AND MGMov.DataMov <= :date_to
            AND CF_TAB.TipoCF LIKE '%C%'
        """
        
        # Filtri condizionali
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR
                    FROM AR AR_Filter
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        params = {
            'date_from': date_from,
            'date_to': date_to,
            'limit': limit
        }
        
        # ✅ STESSI FILTRI (senza clienti_include/exclude)
        if magazzini and len(magazzini) > 0:
            placeholders = ','.join([f':mg_{i}' for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f'mg_{i}'] = mg
        
        if articoli_include and len(articoli_include) > 0:
            placeholders = ','.join([f':art_inc_{i}' for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f'art_inc_{i}'] = art
                
        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ','.join([f':art_exc_{i}' for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f'art_exc_{i}'] = art
        
        if categorie and len(categorie) > 0:
            placeholders = ','.join([f':cat_{i}' for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f'cat_{i}'] = cat
        
        if marche and len(marche) > 0:
            placeholders = ','.join([f':marca_{i}' for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f'marca_{i}'] = marca
        
        if clienti_include and len(clienti_include) > 0:
            placeholders = ','.join([f':cli_inc_{i}' for i in range(len(clienti_include))])
            query += f" AND CF_TAB.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f'cli_inc_{i}'] = cli
                
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ','.join([f':cli_exc_{i}' for i in range(len(clienti_exclude))])
            query += f" AND CF_TAB.Cd_CF NOT IN ({placeholders})"
            for i, cli in enumerate(clienti_exclude):
                params[f'cli_exc_{i}'] = cli

        query += """
        GROUP BY CF_TAB.Cd_CF, CF_TAB.Descrizione
        ORDER BY Valore_Totale DESC
        """
        
        return self.execute_query(query, params)


    def get_articles_sales_summary(self, date_from, date_to, 
                                    exclude_obsolete=True, 
                                    exclude_attribute_18=True,
                                    magazzini=None, categorie=None, 
                                    marche=None, articoli_include=None, 
                                    articoli_exclude=None,
                                    clienti_include=None, 
                                    clienti_exclude=None, **kwargs):
        """
        Ottiene il riepilogo vendite per articolo con dettagli aggregati
        """
        
        query = """
        WITH MovimentiVendita AS (
            SELECT
                MGMov.Cd_AR,
                DOTes.Cd_CF,
                MGMov.DataMov,
                DOTes.NumeroDoc,
                SUM(MGMov.Quantita) AS Quantita_PZ,
                SUM(MGMov.Valore) AS Valore
            FROM MGMov
                INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
                LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
                LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
                LEFT JOIN CF ON CF.Cd_CF = DOTes.Cd_CF
            WHERE 
                MGMov.DataMov >= :date_from
                AND MGMov.DataMov <= :date_to
                AND MGMov.ScaV = 1  -- Solo movimenti in uscita (vendite)
                AND DOTes.Cd_CF IS NOT NULL  -- Solo documenti con cliente
        """
        
        params = {
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Filtri condizionali
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR 
                    FROM AR AR_Filter 
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        # Filtri magazzini
        if magazzini and len(magazzini) > 0:
            placeholders = ','.join([f':mg_{i}' for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f'mg_{i}'] = mg
        
        # Filtri articoli - include
        if articoli_include and len(articoli_include) > 0:
            placeholders = ','.join([f':art_inc_{i}' for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f'art_inc_{i}'] = art
        
        # Filtri articoli - exclude
        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ','.join([f':art_exc_{i}' for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f'art_exc_{i}'] = art
        
        # Filtri categorie
        if categorie and len(categorie) > 0:
            placeholders = ','.join([f':cat_{i}' for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f'cat_{i}'] = cat
        
        # Filtri marche
        if marche and len(marche) > 0:
            placeholders = ','.join([f':marca_{i}' for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f'marca_{i}'] = marca
        
        # Filtri clienti - include
        if clienti_include and len(clienti_include) > 0:
            placeholders = ','.join([f':cli_inc_{i}' for i in range(len(clienti_include))])
            query += f" AND CF.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f'cli_inc_{i}'] = cli
        
        # Filtri clienti - exclude
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ','.join([f':cli_exc_{i}' for i in range(len(clienti_exclude))])
            query += f" AND CF.Cd_CF NOT IN ({placeholders})"
            for i, cli in enumerate(clienti_exclude):
                params[f'cli_exc_{i}'] = cli
        
        query += """
            GROUP BY MGMov.Cd_AR, DOTes.Cd_CF, MGMov.DataMov, DOTes.NumeroDoc
        ),
        
        GiacenzaMagazzino AS (
            SELECT 
                MGDisp.cd_ar,
                SUM(MGDisp.Quantita) AS Giacenza_MG00002
            FROM dbo.Mgdisp(YEAR(GETDATE())) MGDisp
            WHERE MGDisp.cd_mg = '00002'
            GROUP BY MGDisp.cd_ar
        )
        
        SELECT
            AR.Cd_AR AS Codice_Articolo,
            AR.Descrizione AS Descrizione,
            ISNULL(ARGruppo1.Descrizione, 'N/A') AS Categoria,
            ISNULL(ARMarca.Descrizione, 'N/A') AS Marca,
            
            SUM(MV.Quantita_PZ) AS Totale_Qta_Venduta_PZ,
            ROUND(SUM(MV.Quantita_PZ) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Totale_Qta_Venduta_CF,
            ROUND(SUM(MV.Valore), 2) AS Totale_Valore_Venduto,
            COUNT(DISTINCT MV.Cd_CF) AS Num_Clienti_Distinti,
            ROUND(ISNULL(G.Giacenza_MG00002, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Giacenza_MG00002_CF
            
        FROM MovimentiVendita MV
            INNER JOIN AR ON AR.Cd_AR = MV.Cd_AR
            LEFT JOIN ARGruppo1 ON AR.Cd_ARGruppo1 = ARGruppo1.Cd_ARGruppo1
            LEFT JOIN ARMarca ON AR.Cd_ARMarca = ARMarca.Cd_ARMarca
            LEFT JOIN ARARMisura CF ON CF.Cd_AR = AR.Cd_AR AND CF.Cd_ARMisura = 'CF'
            LEFT JOIN GiacenzaMagazzino G ON G.cd_ar = AR.Cd_AR
        
        GROUP BY 
            AR.Cd_AR, AR.Descrizione, ARGruppo1.Descrizione, 
            ARMarca.Descrizione, CF.UMFatt, G.Giacenza_MG00002
        
        ORDER BY Totale_Valore_Venduto DESC
        """
        
        return self.execute_query(query, params)


    def get_clients_by_article(self, cd_ar, date_from, date_to,
                            exclude_obsolete=True, 
                            exclude_attribute_18=True,
                            magazzini=None, categorie=None, 
                            marche=None, articoli_include=None, 
                            articoli_exclude=None,
                            clienti_include=None, 
                            clienti_exclude=None, **kwargs):
        """
        Ottiene il dettaglio clienti per un singolo articolo
        """
        
        query = """
        WITH MovimentiCliente AS (
            SELECT
                DOTes.Cd_CF,
                MGMov.DataMov,
                DOTes.NumeroDoc,
                DOTes.DataDoc,
                SUM(MGMov.Quantita) AS Quantita_PZ,
                SUM(MGMov.Valore) AS Valore
            FROM MGMov
                INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
                LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
                LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
                LEFT JOIN CF ON CF.Cd_CF = DOTes.Cd_CF
            WHERE 
                MGMov.Cd_AR = :cd_ar
                AND MGMov.DataMov >= :date_from
                AND MGMov.DataMov <= :date_to
                AND MGMov.ScaV = 1
                AND DOTes.Cd_CF IS NOT NULL
        """
        
        params = {
            'cd_ar': cd_ar,
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Applica stessi filtri della query principale
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR 
                    FROM AR AR_Filter 
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        if magazzini and len(magazzini) > 0:
            placeholders = ','.join([f':mg_{i}' for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f'mg_{i}'] = mg
        
        if clienti_include and len(clienti_include) > 0:
            placeholders = ','.join([f':cli_inc_{i}' for i in range(len(clienti_include))])
            query += f" AND CF.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f'cli_inc_{i}'] = cli
        
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ','.join([f':cli_exc_{i}' for i in range(len(clienti_exclude))])
            query += f" AND CF.Cd_CF NOT IN ({placeholders})"
            for i, cli in enumerate(clienti_exclude):
                params[f'cli_exc_{i}'] = cli
        
        query += """
            GROUP BY DOTes.Cd_CF, MGMov.DataMov, DOTes.NumeroDoc, DOTes.DataDoc
        )
        
        SELECT
            CF.Cd_CF AS Codice_Cliente,
            CF.Descrizione AS Ragione_Sociale,
            SUM(MC.Quantita_PZ) AS Qta_Venduta_PZ,
            ROUND(SUM(MC.Quantita_PZ) / NULLIF(ISNULL(CFM.UMFatt, 1), 0), 2) AS Qta_Venduta_CF,
            ROUND(SUM(MC.Valore), 2) AS Valore_Venduto,
            COUNT(DISTINCT MC.NumeroDoc) AS Num_Documenti,
            MIN(MC.DataMov) AS Prima_Vendita,
            MAX(MC.DataMov) AS Ultima_Vendita
            
        FROM MovimentiCliente MC
            INNER JOIN CF ON CF.Cd_CF = MC.Cd_CF
            LEFT JOIN ARARMisura CFM ON CFM.Cd_AR = :cd_ar AND CFM.Cd_ARMisura = 'CF'
        
        GROUP BY CF.Cd_CF, CF.Descrizione, CFM.UMFatt
        ORDER BY Valore_Venduto DESC
        """
        
        return self.execute_query(query, params)


    def get_documents_by_article_client(self, cd_ar, cd_cf, date_from, date_to, **kwargs):
        """
        Ottiene l'elenco documenti per un articolo e cliente specifico
        """
        
        query = """
        SELECT
            DOTes.Cd_DO AS Tipo_Documento,
            DOTes.NumeroDoc AS Numero_Documento,
            DOTes.DataDoc AS Data_Documento,
            ROUND(SUM(MGMov.Valore), 2) AS Valore
        FROM MGMov
            LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
            LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
        WHERE 
            MGMov.Cd_AR = :cd_ar
            AND DOTes.Cd_CF = :cd_cf
            AND MGMov.DataMov >= :date_from
            AND MGMov.DataMov <= :date_to
            AND MGMov.ScaV = 1
            AND DOTes.NumeroDoc IS NOT NULL
        GROUP BY DOTes.Cd_DO, DOTes.NumeroDoc, DOTes.DataDoc
        ORDER BY DOTes.DataDoc DESC
        """
        
        params = {
            'cd_ar': cd_ar,
            'cd_cf': cd_cf,
            'date_from': date_from,
            'date_to': date_to
        }
        
        return self.execute_query(query, params)


    def get_monthly_breakdown(self, year, include_all_articles=False, exclude_obsolete=True, exclude_attribute_18=True,
                            magazzini=None, categorie=None, marche=None, 
                            articoli_include=None, articoli_exclude=None,
                            clienti_include=None, clienti_exclude=None, **kwargs):
        """Breakdown mensile (in CF) per anno: sempre una riga per articolo, con filtri opzionali."""

        query = """
        WITH MovimentiBase AS (
            SELECT
                MgMov.Cd_AR,
                MgMov.DataMov AS Data,
                SUM(MgMov.Quantita * MgMov.ScaV) AS QuantitaV,
                SUM(MgMov.Valore * MgMov.ScaV) AS ValoreV,
                SUM(MgMov.Quantita * MgMov.ScaV * ISNULL(CS.Costo, 0)) AS CostoV
            FROM MGMov
                INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
                LEFT JOIN MGMovInt ON MGMov.Id_MGMovInt = MGMovInt.Id_MGMovInt
                LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
                LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
                LEFT JOIN CF CF_TAB ON CF_TAB.Cd_CF = DOTes.Cd_CF
                LEFT JOIN MGCausale ON MGCausale.Cd_MGCausale = ISNULL(DORig.Cd_MGCausale, MGMovInt.Cd_MGCausale)
                LEFT JOIN ARCostoItem CS
                    ON CS.Cd_AR = MGMov.Cd_AR
                    AND CS.TipoCosto = 'U'
                    AND CS.Cd_MGEsercizio = YEAR(GETDATE())
            WHERE
                YEAR(MgMov.DataMov) = :year
        """

        # Aggiungi filtri condizionali
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR 
                    FROM AR AR_Filter 
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        params = {'year': year}
        
        # Filtri magazzini
        if magazzini and len(magazzini) > 0:
            placeholders = ','.join([f':mg_{i}' for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f'mg_{i}'] = mg

        # Filtri articoli - include
        if articoli_include and len(articoli_include) > 0:
            placeholders = ','.join([f':art_inc_{i}' for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f'art_inc_{i}'] = art

        # Filtri articoli - exclude
        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ','.join([f':art_exc_{i}' for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f'art_exc_{i}'] = art

        # Filtri categorie
        if categorie and len(categorie) > 0:
            placeholders = ','.join([f':cat_{i}' for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f'cat_{i}'] = cat

        # Filtri marche
        if marche and len(marche) > 0:
            placeholders = ','.join([f':marca_{i}' for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f'marca_{i}'] = marca

        # Filtri clienti - include (SOLO movimenti di quei clienti)
        if clienti_include and len(clienti_include) > 0:
            placeholders = ','.join([f':cli_inc_{i}' for i in range(len(clienti_include))])
            query += f" AND CF_TAB.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f'cli_inc_{i}'] = cli

        # Filtri clienti - exclude
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ','.join([f':cli_exc_{i}' for i in range(len(clienti_exclude))])
            query += f" AND (CF_TAB.Cd_CF NOT IN ({placeholders}) OR CF_TAB.Cd_CF IS NULL)"
            for i, cli in enumerate(clienti_exclude):
                params[f'cli_exc_{i}'] = cli

        query += """
            GROUP BY MgMov.Cd_AR, MgMov.DataMov, CF_TAB.Cd_CF
        )

        SELECT
            AR.Cd_AR AS Codice,
            AR.Descrizione AS Descrizione_AR,

            ROUND(SUM(CASE WHEN MONTH(S.Data) = 1  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Gennaio,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 2  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Febbraio,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 3  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Marzo,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 4  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Aprile,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 5  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Maggio,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 6  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Giugno,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 7  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Luglio,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 8  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Agosto,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 9  THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Settembre,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 10 THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Ottobre,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 11 THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Novembre,
            ROUND(SUM(CASE WHEN MONTH(S.Data) = 12 THEN S.QuantitaV / NULLIF(ISNULL(CF.UMFatt,1),0) ELSE 0 END), 2) AS Dicembre,

            ROUND(SUM(S.QuantitaV) / NULLIF(ISNULL(CF.UMFatt,1),0), 2) AS Totale_Anno
        """

        if include_all_articles:
            query += """
            FROM AR
            LEFT JOIN MovimentiBase S ON AR.Cd_AR = S.Cd_AR
            """
        else:
            query += """
            FROM MovimentiBase S
            INNER JOIN AR ON AR.Cd_AR = S.Cd_AR
            """
            
        query += """    
        LEFT JOIN ARARMisura CF ON CF.Cd_AR = AR.Cd_AR AND CF.Cd_ARMisura = 'CF'
        
        GROUP BY AR.Cd_AR, AR.Descrizione, CF.UMFatt
        HAVING SUM(S.QuantitaV) > 0
        ORDER BY AR.Cd_AR
        """
        
        return self.execute_query(query, params)
    
    def get_order_planning(self, date_from, date_to, target_months, 
                        exclude_obsolete=True, exclude_attribute_18=True,
                        magazzini=None, categorie=None, marche=None, 
                        articoli_include=None, articoli_exclude=None,
                        clienti_include=None, clienti_exclude=None, **kwargs):
        """Query per pianificazione ordini con formula semplice e mesi di copertura configurabili"""
        
        query = """
        WITH MovimentiBase AS (
            SELECT
                MGMov.Cd_AR,
                SUM(MGMov.Quantita * MGMov.ScaV) AS TotaleQuantita
            FROM MGMov
                INNER JOIN AR ON AR.Cd_AR = MGMov.Cd_AR
                LEFT JOIN MGMovInt ON MGMov.Id_MGMovInt = MGMovInt.Id_MGMovInt
                LEFT JOIN DORig ON DORig.Id_DORig = MGMov.Id_DORig
                LEFT JOIN DOTes ON DOTes.Id_DOTes = DORig.Id_DOTes
                LEFT JOIN CF ON CF.Cd_CF = DOTes.Cd_CF
                LEFT JOIN MGCausale ON MGCausale.Cd_MGCausale = ISNULL(DORig.Cd_MGCausale, MGMovInt.Cd_MGCausale)
            WHERE 
                MGMov.DataMov >= :date_from
                AND MGMov.DataMov <= :date_to
        """
        
        # Filtri condizionali
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
        
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR 
                    FROM AR AR_Filter 
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        params = {
            'date_from': date_from,
            'date_to': date_to,
            'target_months': target_months
        }
        
        # Magazzini
        if magazzini and len(magazzini) > 0:
            placeholders = ",".join([f":mg_{i}" for i in range(len(magazzini))])
            query += f" AND MGMov.Cd_MG IN ({placeholders})"
            for i, mg in enumerate(magazzini):
                params[f"mg_{i}"] = mg

        # Articoli include
        if articoli_include and len(articoli_include) > 0:
            placeholders = ",".join([f":art_inc_{i}" for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f"art_inc_{i}"] = art

        # Articoli exclude
        if articoli_exclude and len(articoli_exclude) > 0:
            placeholders = ",".join([f":art_exc_{i}" for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f"art_exc_{i}"] = art

        # Categorie
        if categorie and len(categorie) > 0:
            placeholders = ",".join([f":cat_{i}" for i in range(len(categorie))])
            query += f" AND AR.Cd_ARGruppo1 IN ({placeholders})"
            for i, cat in enumerate(categorie):
                params[f"cat_{i}"] = cat

        # Marche
        if marche and len(marche) > 0:
            placeholders = ",".join([f":marca_{i}" for i in range(len(marche))])
            query += f" AND AR.Cd_ARMarca IN ({placeholders})"
            for i, marca in enumerate(marche):
                params[f"marca_{i}"] = marca

        # Clienti include
        if clienti_include and len(clienti_include) > 0:
            placeholders = ",".join([f":cli_inc_{i}" for i in range(len(clienti_include))])
            query += f" AND DOTes.Cd_CF IN ({placeholders})"
            for i, cli in enumerate(clienti_include):
                params[f"cli_inc_{i}"] = cli

        # Clienti exclude
        if clienti_exclude and len(clienti_exclude) > 0:
            placeholders = ",".join([f":cli_exc_{i}" for i in range(len(clienti_exclude))])
            query += f" AND DOTes.Cd_CF NOT IN ({placeholders})"
            for i, cli in enumerate(clienti_exclude):
                params[f"cli_exc_{i}"] = cli
        
        # Ora il group by include anche il cliente
        query += """
            GROUP BY MGMov.Cd_AR
        ),

        GiacenzeArticolo AS (
            SELECT 
                MGDisp.cd_ar,
                SUM(MGDisp.Quantita) AS TotaleGiacenza,
                SUM(MGDisp.ImpQ) AS TotaleImpegnato,
                SUM(MGDisp.OrdQ) AS TotaleOrdinato
            FROM dbo.Mgdisp(YEAR(GETDATE())) MGDisp
            INNER JOIN AR ON AR.Cd_AR = MGDisp.cd_ar
            WHERE MGDisp.cd_ar IN (SELECT Cd_AR FROM MovimentiBase)
        """
        
        if exclude_obsolete:
            query += " AND AR.Obsoleto = '0'"
            
        if exclude_attribute_18:
            query += """
                AND AR.Cd_AR NOT IN (
                    SELECT AR_Filter.Cd_AR 
                    FROM AR AR_Filter 
                    WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
                )
            """
        
        query += """
            GROUP BY MGDisp.cd_ar
        )
        
        SELECT
            AR.Cd_AR AS Codice,
            AR.Descrizione AS Descrizione_AR,
            ISNULL(CAST(ARAlias.EAN_Code AS VARCHAR(20)), 'N/A') + '' AS [EAN_(PZ)],
            --ISNULL(ARGruppo1.Descrizione, 'N/A') AS Categoria,
            --ISNULL(ARMarca.Descrizione, 'N/A') AS Marca,     

            ROUND(
                (
                    (:target_months / NULLIF(DATEDIFF(month, :date_from, :date_to), 0))
                    * ((ISNULL(M.TotaleQuantita, 0) + ISNULL(G.TotaleImpegnato, 0)) / NULLIF(ISNULL(CA.UMFatt, 1), 0))
                    - ((ISNULL(G.TotaleGiacenza, 0) + ISNULL(G.TotaleOrdinato, 0)) / NULLIF(ISNULL(CA.UMFatt, 1), 0))
                    + (ISNULL(G.TotaleImpegnato, 0) / NULLIF(ISNULL(CA.UMFatt, 1), 0))
                )
            ,1) AS Qta_da_Ordinare_CA, 

            -- 1. Prima calcola CF arrotondato (a intero)
            ROUND(
                (
                    (:target_months / NULLIF(DATEDIFF(month, :date_from, :date_to), 0))
                    * ((ISNULL(M.TotaleQuantita, 0) + ISNULL(G.TotaleImpegnato, 0)) / NULLIF(ISNULL(CF.UMFatt, 1), 0))
                    - ((ISNULL(G.TotaleGiacenza, 0) + ISNULL(G.TotaleOrdinato, 0)) / NULLIF(ISNULL(CF.UMFatt, 1), 0))
                    + (ISNULL(G.TotaleImpegnato, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0))
                )
            , 0) AS Qta_da_Ordinare_CF,

            -- 2. Nuovo calcolo PZ basato su CF arrotondato
            ROUND(
                (
                    (:target_months / NULLIF(DATEDIFF(month, :date_from, :date_to), 0))
                    * ((ISNULL(M.TotaleQuantita, 0) + ISNULL(G.TotaleImpegnato, 0)) / NULLIF(ISNULL(CF.UMFatt, 1), 0))
                    - ((ISNULL(G.TotaleGiacenza, 0) + ISNULL(G.TotaleOrdinato, 0)) / NULLIF(ISNULL(CF.UMFatt, 1), 0))
                    + (ISNULL(G.TotaleImpegnato, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0))
                )
            , 0) * ISNULL(CF.UMFatt, 1) AS Qta_da_Ordinare_PZ,

            -- 3. Il vecchio calcolo PZ diventa PZ_Base (calcolo originale)
            ROUND(
                (
                    (:target_months / NULLIF(DATEDIFF(month, :date_from, :date_to), 0))
                    * (ISNULL(M.TotaleQuantita, 0) + ISNULL(G.TotaleImpegnato, 0))
                    - (ISNULL(G.TotaleGiacenza, 0) + ISNULL(G.TotaleOrdinato, 0))
                    + ISNULL(G.TotaleImpegnato, 0)
                )
            , 0) AS Qta_da_Ordinare_PZ_Base,

            ISNULL(CF.UMFatt, 1) AS [PZ x CF],
            ISNULL(CA.UMFatt, 1) AS [PZ x CA],
            ISNULL(PL.UMFatt, 1) AS [PZ x PL],

            CASE 
                WHEN ISNULL(M.TotaleQuantita, 0) = 0 THEN 0 
                ELSE ROUND(
                    (
                        ((ISNULL(G.TotaleOrdinato, 0) + ISNULL(G.TotaleGiacenza, 0)) 
                        - ISNULL(G.TotaleImpegnato, 0)) 
                        / (M.TotaleQuantita + G.TotaleImpegnato)
                    ) * 2, 2
                )
            END AS Mesi_Coperti,

            ROUND(ISNULL(G.TotaleGiacenza, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Giacenza_Attuale_CF,
            ROUND(ISNULL(G.TotaleOrdinato, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Ordinato_Fornitori_CF,
            ROUND(ISNULL(M.TotaleQuantita, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Venduto_Periodo_CF,
            ROUND(ISNULL(G.TotaleImpegnato, 0) / NULLIF(ISNULL(CF.UMFatt, 1), 0), 2) AS Impegnato_Clienti_CF,

            ISNULL((
                SELECT CONVERT(NUMERIC(18,4), ROUND(Costo, 4))
                FROM [dbo].ARCostoItem 
                WHERE TipoCosto = 'U' 
                AND Cd_MGEsercizio = YEAR(GETDATE())
                AND CD_AR = AR.CD_AR
            ), 0) AS [UltCost_(PZ)],

            ISNULL((
                SELECT CONVERT(NUMERIC(18,2), LSArticolo.prezzo)
                FROM [dbo].LSArticolo
                WHERE CD_AR = AR.CD_AR 
                AND LSArticolo.id_lsrevisione = 2
            ), 0) AS [Prz_B2B_(PZ)],

            CAST(AR.xWcScadenza AS DATE) AS Scadenza


            
        FROM MovimentiBase M
        INNER JOIN AR ON AR.Cd_AR = M.Cd_AR
        LEFT JOIN ARGruppo1 ON AR.Cd_ARGruppo1 = ARGruppo1.Cd_ARGruppo1
        LEFT JOIN ARMarca ON AR.Cd_ARMarca = ARMarca.Cd_ARMarca
        LEFT JOIN GiacenzeArticolo G ON G.cd_ar = M.Cd_AR
        LEFT JOIN ARARMisura CF ON CF.Cd_AR = AR.Cd_AR AND CF.Cd_ARMisura = 'CF'
        LEFT JOIN ARARMisura CA ON CA.Cd_AR = AR.Cd_AR AND CA.Cd_ARMisura = 'CA'
        LEFT JOIN ARARMisura PL ON PL.Cd_AR = AR.Cd_AR AND PL.Cd_ARMisura = 'PL'
        LEFT JOIN (
            SELECT 
                Cd_AR,
                Alias AS EAN_Code  -- Prendi Alias come stringa SENZA conversioni
            FROM (
                SELECT 
                    Cd_AR,
                    Alias,
                    Cd_ARMisura,
                    TipoAlias,
                    ROW_NUMBER() OVER (
                        PARTITION BY Cd_AR 
                        ORDER BY 
                            CASE 
                                WHEN Cd_ARMisura LIKE '%PZ%' AND TipoAlias = 'E' THEN 1
                                WHEN TipoAlias LIKE '%E%' THEN 2
                                WHEN Cd_ARMisura LIKE '%PZ%' THEN 3
                                ELSE 4
                            END,
                            Alias  -- In caso di parità, prendi il primo alfabeticamente
                    ) AS rn
                FROM ARAlias
                WHERE Cd_ARMisura LIKE '%PZ%' OR TipoAlias LIKE '%E%'
            ) ranked
            WHERE rn = 1
        ) AS ARAlias ON ARAlias.Cd_AR = AR.Cd_AR
        
        WHERE 1=1
        """

        # Filtri articoli finali
        if articoli_include:
            placeholders = ','.join([f':art_inc_{i}' for i in range(len(articoli_include))])
            query += f" AND AR.Cd_AR IN ({placeholders})"
            for i, art in enumerate(articoli_include):
                params[f'art_inc_{i}'] = art

        if articoli_exclude:
            placeholders = ','.join([f':art_exc_{i}' for i in range(len(articoli_exclude))])
            query += f" AND AR.Cd_AR NOT IN ({placeholders})"
            for i, art in enumerate(articoli_exclude):
                params[f'art_exc_{i}'] = art

        if exclude_attribute_18:
            query += """
            AND AR.Cd_AR NOT IN (
                SELECT AR_Filter.Cd_AR 
                FROM AR AR_Filter 
                WHERE ISNULL(CONVERT(VARCHAR(MAX), AR_Filter.Attributi), '') LIKE '%attributo="18"%'
            )
            """

        query += " ORDER BY AR.Cd_AR"
        
        return self.execute_query(query, params)
    



"""
-- Query Debug da lanciare in SSMS -- 

-- -- -- -- -- -- -- -- -- --

    Query di debug per Note di Credito Cliente (NCC)
    Utilizzata per verificare le NCC emesse in un periodo specifico.
    La prima parte elenca le righe di dettaglio con data, articolo e importo.
    La seconda calcola il totale delle NCC (escludendo valori zero e righe senza articolo)
    che viene sottratto dal Valore Totale per ottenere il Valore Netto.
    Permette di identificare le NCC "orfane" (articoli rimborsati ma non venduti)
    e verificare l'allineamento tra le diverse query.

    Eseguire in SSMS sostituendo le date con il periodo da analizzare:

    SELECT 
        T.DataDoc,
        R.Cd_AR,
        R.PrezzoTotaleV,
        T.Cd_Do,
        T.NumeroDoc
    FROM DOTes T
    INNER JOIN DORig R ON R.Id_DOTes = T.Id_DOTes
    WHERE T.Cd_Do = 'NCC'
        AND TRY_CONVERT(date, T.DataDoc, 23) BETWEEN '2025-09-01' AND '2025-09-29'
        AND R.PrezzoTotaleV <> 0
    ORDER BY T.DataDoc, R.Cd_AR

    -- Totale NCC filtrato:
    SELECT SUM(R.PrezzoTotaleV) AS NCC_Totale
    FROM DOTes T
    INNER JOIN DORig R ON R.Id_DOTes = T.Id_DOTes
    WHERE T.Cd_Do = 'NCC'
        AND TRY_CONVERT(date, T.DataDoc, 23) BETWEEN '2025-09-01' AND '2025-09-29'
        AND R.PrezzoTotaleV <> 0
        AND R.Cd_AR IS NOT NULL

-- -- -- -- -- -- -- -- -- --

Query di debug per NCC "orfane" (articoli con Note di Credito ma senza vendite)
Identifica articoli presenti in NCC emesse nel periodo ma che non hanno avuto
movimenti di magazzino (vendite). Questi articoli sono stati rimborsati ai clienti
ma non venduti nel range selezionato. Utilizzata per verificare la coerenza tra
il totale delle cards (Articoli_Totali) e le righe della tabella dettaglio.

Eseguire in SSMS sostituendo date e magazzini:

SELECT 
    R.Cd_AR,
    SUM(R.PrezzoTotaleV) AS NCC_Senza_Movimenti
FROM DOTes T
INNER JOIN DORig R ON R.Id_DOTes = T.Id_DOTes
WHERE T.Cd_Do = 'NCC'
    AND TRY_CONVERT(date, T.DataDoc, 23) BETWEEN '2025-09-01' AND '2025-09-29'
    AND R.PrezzoTotaleV <> 0
    AND R.Cd_AR IS NOT NULL
    AND R.Cd_AR NOT IN (
        SELECT DISTINCT Cd_AR 
        FROM MGMov 
        WHERE TRY_CONVERT(date, MGMov.DataMov, 23) BETWEEN '2025-09-01' AND '2025-09-29'
            AND MGMov.Cd_MG IN ('00001', '00002')
    )
GROUP BY R.Cd_AR

-- -- -- -- -- -- -- -- -- --
"""