from duckduckgo_search import DDGS

print("Starte Test-Suche...")
try:
    with DDGS() as ddgs:
        results = [r for r in ddgs.text("Healthcare in the USA", max_results=3)]
        print("ERFOLG! Suche hat Ergebnisse geliefert:")
        print(results)
except Exception as e:
    print("FEHLER BEI DER SUCHE:")
    print(str(e))