# För tillgång till test EDI & TIS
I utforskaren högerklicka på ’Den här datorn’. Lägg till en nätverksplats
•	Document store TEST (fraktsedlar och blandade dokument): https://documentstorewebdav-development.nowastelogistics.com
•	EDI Atria TEST: https://ediservicewebdav-development-atria.nowastelogistics.com
•	EDI Frey TEST: https://ediservicewebdav-development-frey.nowastelogistics.com
•	EDI ItWorks TEST: https://ediservicewebdav-development-itworks.nowastelogistics.com
•	EDI Loki TEST: https://ediservicewebdav-development-loki.nowastelogistics.com
•	EDI Mestergruppen TEST: https://ediservicewebdav-development-mestergruppen.nowastelogistics.com
•	TIS ItWorks TEST: https://tiscustomswebdav-development-itworks.nowastelogistics.com
•	TIS Mi17 TEST: https://tiscustomswebdav-development-mi17.nowastelogistics.com
 
Användarnamn: newadmin
Lösenord: newpassword
# För att leta fram fraktsedlar
Ladda ner Bruno. Applikation med Hund som ikon. 
Öppna anteckningar - > klistra in nedan -> spara filen som kundnamn.bru i sökvägen för Bruno > Sen är det bara att öppna Bruno
Granngården
```text
meta {
  name: Granngården
  type: http
  seq: 2
}

get {
  url: http://nowastedocuments2.nowastelogistics.com/Document/ViewDeliveryNote?orderId=TO100026664&company=GG&shipmentId=GG-404-250625-1704125-0-
  body: none
  auth: inherit
}

params:query {
  orderId: TO100026664
  company: GG
  shipmentId: GG-404-250625-1704125-0-
}
Peak Performance
meta {
  name: PeakPerformance
  type: http
  seq: 1
}

get {
  url: http://nowastedocuments-development.nowastelogistics.com/Document/ViewDeliveryNoteForOrderPdf?orderId=4055803352&company=PEA
  body: none
  auth: inherit
}

params:query {
  orderId: 4055803352
  company: PEA
}
Granngården Test
meta {
  name: Granngården Test
  type: http
  seq: 5
}

get {
  url: http://nowastedocuments2-development.nowastelogistics.com/Document/ViewDeliveryNote?orderId=T03100025755&company=GG&shipmentId=3538971429
  body: none
  auth: inherit
}

params:query {
  orderId: T03100025755
  company: GG
  shipmentId: 3538971429
}
```
# Orderlinjer i status 31 vid möjlig automation
För att slå på, ändra effect optioner – 225 till 
Skicka ordrar i test
Skapa en excell efter tömningsordermallen men välj kund som finns i test registret. Ladda upp denna på https://api.nowaste.se/NowasteOrder/ -> Log -> Import Excell -> ladda upp din excell 
För att kunna återrapportera order i test
Sätt dummy transportör och trigga shipment sen testa igen. Glöm inte avisera
Logik för bokstav bakom pall:id VM-Etikett

```sql
  -- Logic 
  IF @company IN ('GG')
  BEGIN

    -- A = Om de finns med i prognosen.
    IF 1 = (SELECT TOP 1 1 FROM [ITEM_FORECAST] WHERE [ITEM_NUM] = @itemId AND [COMPANY] = @company AND GETDATE() BETWEEN [FROM_DATE] AND [TO_DATE])
      SET @expectedItemPriority = 'A'
    -- P = Om den har plockplats som inte finns i LOCATION_CRANE (grav-banor).
    ELSE IF 1 = (SELECT TOP 1 1 FROM [BATCH_STOCK] WHERE [ITEM_NUM] = @itemId AND [COMPANY] = @company AND [WAREH_NUM] = @warehouse AND [LOCATION] NOT IN (SELECT [LOCATION] FROM [LOCATION_CRANE]))
      SET @expectedItemPriority = 'P'
    -- K = Allt annat.
    ELSE
      SET @expectedItemPriority = 'K'
```
# SPC Verifikation
För att skriva in pallnummer istället för checksiffra för spc.
I Zon plock behöver kolumnen Ingen check vara N och Effect option 582 vara Y.
 
 
# Brandfarliga etiketter utskrift
För att starta så att det skrivs ut vid plock. 
Sök ord: ADR, Brandfarligt, lq, un, Klass 9 , Frästande gods.
Effectoption 150 & 151 Samt overrides för när den ska triggas
Såhär ser dem inställningarna ut
 
 
Om man vill aktivera/inaktivera etiketterna för en specifik transportör så gör man såhär i override för option 151
 
 
 company:transnr
Skriver man in i override så utesluts dessa bolag och transnummer från etiketterna.
# Hur fungerar logiken plockpresentationslogg
```sql
WITH PalletCounts AS (
    SELECT 
        ORDER_NUM,
    CUSTOM_NUM,
        LINE_NUM, 
        ITEM_NUM, 
        WAREH_NUM, 
        COMPANY, 
        PICK_ZONE, 
        CAST(COUNT(DISTINCT PALL_NUM) AS FLOAT) AS PALLETS
    FROM PICK_LOG
    WHERE ISNULL(PALL_NUM, 0) > 0
  AND CUSTOM_NUM NOT IN ('888','999')
    GROUP BY ORDER_NUM, LINE_NUM, ITEM_NUM, WAREH_NUM, COMPANY, PICK_ZONE, CUSTOM_NUM
),
QtySufSummed AS (
    SELECT 
        COMPANY,
        WAREH_NUM,
    CUSTOM_NUM,
        ITEM_NUM,
        ORDER_NUM,
        LINE_NUM,
        PICK_ZONE,
        SUM(QTY_PRE) AS QTY_SUF_SUM
    FROM PICK_LOG
    WHERE QTY_SUF > 0
  AND CUSTOM_NUM NOT IN ('888','999', '6005')
    GROUP BY COMPANY, WAREH_NUM, ITEM_NUM, ORDER_NUM, LINE_NUM, PICK_ZONE, CUSTOM_NUM
),
QtySufRanked AS (
    SELECT
        COMPANY,
        WAREH_NUM,
        ITEM_NUM,
        PICK_ZONE,
    CUSTOM_NUM,
        QTY_SUF_SUM,
        ROW_NUMBER() OVER (
            PARTITION BY ITEM_NUM, COMPANY, WAREH_NUM, PICK_ZONE
            ORDER BY QTY_SUF_SUM
        ) AS PARTITION_ROW,
        COUNT(*) OVER (
            PARTITION BY ITEM_NUM, COMPANY, WAREH_NUM, PICK_ZONE
        ) AS PARTITION_COUNT
    FROM QtySufSummed
),
QtySufMedian AS (
    SELECT
        COMPANY,
        WAREH_NUM,
        ITEM_NUM,
        PICK_ZONE,
        CAST(AVG(QTY_SUF_SUM) AS INT) AS MEDIAN_QTY_SUF
    FROM QtySufRanked
    WHERE 
        PARTITION_ROW = (PARTITION_COUNT + 1) / 2 OR
        PARTITION_ROW = (PARTITION_COUNT + 2) / 2
    GROUP BY COMPANY, WAREH_NUM, ITEM_NUM, PICK_ZONE
),
QtySufAvgPreGrouped AS (
    SELECT 
        COMPANY,
        WAREH_NUM,
        ITEM_NUM,
        ORDER_NUM,
        LINE_NUM,
        PICK_ZONE,
        SUM(QTY_PRE) AS SUM_QTY_SUF
    FROM PICK_LOG
    WHERE QTY_SUF > 0
  AND CUSTOM_NUM NOT IN ('888','999')
    GROUP BY COMPANY, WAREH_NUM, ITEM_NUM, ORDER_NUM, LINE_NUM, PICK_ZONE, CUSTOM_NUM
),
QtySufAvgFinal AS (
    SELECT 
        COMPANY,
        WAREH_NUM,
        ITEM_NUM,
        PICK_ZONE,
        AVG(SUM_QTY_SUF) AS AVG_QTY_SUF
    FROM QtySufAvgPreGrouped
    GROUP BY COMPANY, WAREH_NUM, ITEM_NUM, PICK_ZONE
)
SELECT 
    PC.ITEM_NUM, 
    PC.WAREH_NUM, 
    PC.COMPANY, 
    PC.PICK_ZONE, 
    ROUND(AVG(PC.PALLETS), 1) AS PALLETS_PER_ORDER,
    CASE
        WHEN PC.PICK_ZONE != 'R' THEN 0
        ELSE COUNT(DISTINCT LEFT(PS.PALL_NUM, LEN(PS.PALL_NUM) - 4))
    END AS AUTOSTORE_BINS,
    ISNULL(MAX(PS.qty), 0) as MAX_QTY,
    I.ROBOT_IND,
    ISNULL(IA.VALUE, 'N') AS CONTROLLED,
    ISNULL(MAX(QM.MEDIAN_QTY_SUF), 0) AS QTY_SUF_MEDIAN,
  ISNULL(MAX(QA.AVG_QTY_SUF), 0) AS QTY_SUF_AVG
FROM PalletCounts PC
LEFT JOIN PALLET_STOCK PS ON PS.ITEM_NUM = PC.ITEM_NUM AND PS.COMPANY = PC.COMPANY AND PS.WAREH_NUM = PC.WAREH_NUM AND PS.LOCATION = 'AUTOSTORE'
LEFT JOIN ITEM I ON PC.ITEM_NUM = I.ITEM_NUM AND PC.COMPANY = I.COMPANY AND PC.WAREH_NUM = I.WAREH_NUM
LEFT JOIN ITEM_ATTRIBUTE IA ON PC.ITEM_NUM = IA.ITEM_NUM AND PC.COMPANY = IA.COMPANY AND PC.WAREH_NUM = IA.WAREH_NUM AND IA.NAME = 'CONTROLLED'
LEFT JOIN QtySufMedian QM ON QM.ITEM_NUM = PC.ITEM_NUM AND QM.COMPANY = PC.COMPANY AND QM.WAREH_NUM = PC.WAREH_NUM AND QM.PICK_ZONE = PC.PICK_ZONE
LEFT JOIN QtySufAvgFinal QA ON QA.ITEM_NUM = PC.ITEM_NUM AND QA.COMPANY = PC.COMPANY AND QA.WAREH_NUM = PC.WAREH_NUM AND QA.PICK_ZONE = PC.PICK_ZONE
GROUP BY 
    PC.ITEM_NUM, 
    PC.WAREH_NUM, 
    PC.COMPANY, 
    PC.PICK_ZONE,
    I.ROBOT_IND,
    PS.LOCATION,
    IA.VALUE
GO
Minutes on belt
WITH StartEvents AS (
    SELECT
        l.COMPANY,
        l.PICK_PALLET_NUM,
        l.[TIMESTAMP] AS StartTime,
        LEAD(l.[TIMESTAMP]) OVER (
            PARTITION BY l.COMPANY, l.PICK_PALLET_NUM
            ORDER BY     l.[TIMESTAMP]
        )             AS NextStartTime
    FROM LOADING_LOG AS l
    WHERE l.TYPE = 202
      AND l.DISPATCH_AREA = 'BANDET'
),
Paired AS (
    SELECT
        s.COMPANY,
        s.PICK_PALLET_NUM,
        s.StartTime,
        e.EndTime,
        e.EndDispatchArea,
        DATEDIFF(MINUTE, s.StartTime, e.EndTime) AS MinutesOnConveyor
    FROM StartEvents AS s
    OUTER APPLY (
        SELECT TOP (1)
            l2.[TIMESTAMP]   AS EndTime,
            l2.DISPATCH_AREA AS EndDispatchArea
        FROM LOADING_LOG AS l2
        WHERE l2.TYPE = 200
          AND l2.COMPANY = s.COMPANY
          AND l2.PICK_PALLET_NUM = s.PICK_PALLET_NUM
          AND l2.[TIMESTAMP] > s.StartTime
          AND (s.NextStartTime IS NULL OR l2.[TIMESTAMP] < s.NextStartTime)
        ORDER BY l2.[TIMESTAMP] ASC
    ) AS e
)
SELECT
    COMPANY,
    CAST(StartTime AS date)          AS DATE,
    DATEPART(HOUR, StartTime)        AS HOUR,
    MinutesOnConveyor                AS MINS_ON_BELT
FROM Paired
WHERE EndTime IS NOT NULL
```

# Ta ut info från arkiv plocklogg via SQL
```sql
SELECT
    p.TYPE,
    p.DEPART_CODE,
    p.PICK_ZONE,
    p.LINE_NUM,
    p.REL_NUM,
    p.CUSTOM_NUM,
    p.ORDER_NUM,
    p.ITEM_NUM,
    p.QTY_PRE,
    p.QTY_SUF,
    p.TimeStampInt,
    p.TIMESTAMP,
    p.WAREH_NUM,
    p.COMPANY,
    p.PICK_PALL_NUM,
    o.CUSTOM_REF,
    o.ORDER_TYPE,
    o.SHIPMENT_ID
FROM wmanfrey.dbo.PICK_LOG p
INNER JOIN wmanfrey.dbo.ORDER_LOG o
    ON p.ORDER_NUM = o.ORDER_NUM
    AND p.COMPANY = o.COMPANY
WHERE p.TIMESTAMP BETWEEN CAST('2025-01-01' AS DATETIME) AND CAST('2025-03-01' AS DATETIME)
UNION ALL
SELECT
    p.TYPE,
    p.DEPART_CODE,
    p.PICK_ZONE,
    p.LINE_NUM,
    p.REL_NUM,
    p.CUSTOM_NUM,
    p.ORDER_NUM,
    p.ITEM_NUM,
    p.QTY_PRE,
    p.QTY_SUF,
    p.TimeStampInt,
    p.TIMESTAMP,
    p.WAREH_NUM,
    p.COMPANY,
    p.PICK_PALL_NUM,
    o.CUSTOM_REF,
    o.ORDER_TYPE,
    o.SHIPMENT_ID
FROM log_wmanfrey.dbo.PICK_LOG p
INNER JOIN log_wmanfrey.dbo.ORDER_LOG o
    ON p.ORDER_NUM = o.ORDER_NUM
    AND p.COMPANY = o.COMPANY
WHERE p.TIMESTAMP BETWEEN CAST('2025-01-01' AS DATETIME) AND CAST('2025-03-01' AS DATETIME)
ORDER BY TIMESTAMP DESC;
   ```

# Script som sätter  attributet measured = Y, 1 gång
```sql
INSERT INTO ITEM_ATTRIBUTE (ITEM_NUM, WAREH_NUM, COMPANY, NAME, VALUE)
SELECT ITEM_NUM, WAREH_NUM, COMPANY, 'measured', 'Y'
FROM ITEM_ATTRIBUTE IA
WHERE [NAME] = 'IntroDate'
  AND CAST([VALUE] AS DATE) < '2025-05-01'
  AND NOT EXISTS (
    SELECT 1
    FROM ITEM_ATTRIBUTE IA2
    WHERE IA2.ITEM_NUM = IA.ITEM_NUM
      AND IA2.WAREH_NUM = IA.WAREH_NUM
      AND IA2.COMPANY = IA.COMPANY
      AND IA2.NAME = 'measured'
  );


SELECT 
    m.ITEM_NUM,
    m.WAREH_NUM,
    m.COMPANY,
    i.VALUE AS IntroDate,
    m.NAME AS MeasuredName,
    m.VALUE AS MeasuredValue
FROM ITEM_ATTRIBUTE m
JOIN ITEM_ATTRIBUTE i
  ON m.ITEM_NUM = i.ITEM_NUM
AND m.WAREH_NUM = i.WAREH_NUM
AND m.COMPANY = i.COMPANY
WHERE m.NAME = 'measured'
  AND i.NAME = 'IntroDate'
  AND CAST(i.VALUE AS DATE) < '2025-05-01'
ORDER BY CAST(i.VALUE AS DATE) DESC;
```