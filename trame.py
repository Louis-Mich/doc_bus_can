import pandas as pd
import re
import struct
import matplotlib.pyplot as plt

def analyseur_audi_integral(filename):
    """Analyseur complet : Métrologie, Éclairage, Freinage Physique vs Logique et Crash Bus."""
    records = []
    unknown_counts = {}
    
    print(f"Démarrage de l'analyse intégrale de {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(';') or not line.strip():
                continue
            
            parts = re.split(r'\s+', line.strip())
            
            if len(parts) >= 5:
                try:
                    time_ms = float(parts[1])
                    frame_type = parts[2]
                    
                    # 1. Capture du "Crash Bus" (Erreurs matérielles)
                    if frame_type in ['ER', 'EC', 'ST']:
                        records.append({
                            'Time': time_ms, 
                            'Type': 'ERREUR_MATERIELLE'
                        })
                        continue
                    
                    # 2. Capture des trames de données (DT)
                    elif frame_type == 'DT' and len(parts) >= 7:
                        can_id = parts[3].upper()
                        dlc = int(parts[5])
                        data_hex = "".join(parts[6:6+dlc])
                        data_bytes = bytes.fromhex(data_hex)
                        
                        entry = {'Time': time_ms, 'Type': 'DONNEE_CAN', 'ID': can_id}
                        parsed = False
                        
                        # --- DÉCODAGE BCM (0x390) : Éclairage et Feux Stop ---
                        if can_id == "0390" and dlc >= 7:
                            entry['Cligno_G'] = 1 if (data_bytes[4] & 0x04) else 0
                            entry['Cligno_D'] = 1 if (data_bytes[4] & 0x08) else 0
                            entry['Warning'] = 1 if (data_bytes[4] & 0x0C) == 0x0C else 0
                            entry['Feux_Stop'] = 1 if (data_bytes[4] & 0x40) else 0 # Output BCM
                            entry['Feu_Recul'] = 1 if (data_bytes[3] & 0x10) else 0
                            entry['Veill_Crois'] = 1 if (data_bytes[6] & 0x30) else 0
                            entry['Antibrouillard'] = 1 if (data_bytes[6] & 0x05) else 0
                            parsed = True

                        # --- DÉCODAGE ABS (0x1A0) : Vitesse et Pédale Physique ---
                        elif can_id == "01A0" and dlc >= 4:
                            entry['Vitesse_ABS'] = ((data_bytes[1] & 0x1F) << 8 | data_bytes[0]) * 0.01
                            entry['Pedale_Frein'] = 1 if (data_bytes[1] & 0x08) else 0 # Input Capteur
                            parsed = True

                        # --- DÉCODAGE Volant (0x5A0) ---
                        elif can_id == "05A0" and dlc >= 2:
                            entry['Angle_Volant'] = struct.unpack('<h', data_bytes[0:2])[0] * 0.1
                            parsed = True
                        
                        # --- DÉCODAGE Moteur (0x0C2) ---
                        elif can_id == "00C2":
                            entry['Couple_Moteur'] = data_bytes[1] * 0.5
                            parsed = True

                        # Tracking des inconnus
                        if not parsed:
                            if can_id not in unknown_counts:
                                unknown_counts[can_id] = 0
                            unknown_counts[can_id] += 1

                        records.append(entry)
                except Exception:
                    continue

    return pd.DataFrame(records), unknown_counts

# --- 1. Exécution de l'extraction ---
df, trames_inconnues = analyseur_audi_integral('Test4.trc')

print("\n--- LISTING DES TRAMES NON DÉCODÉES ---")
for can_id, count in sorted(trames_inconnues.items(), key=lambda x: x[1], reverse=True):
    print(f"ID {can_id} : {count} occurrences ignorées")

# --- 2. Préparation des jeux de données pour les graphiques ---
erreurs_bus = df[df['Type'] == 'ERREUR_MATERIELLE']['Time']
bcm = df.dropna(subset=['Veill_Crois'])     # Trames 0x390
abs_data = df.dropna(subset=['Pedale_Frein']) # Trames 0x1A0

def ajouter_crash_bus(plt_obj):
    """Ajoute des lignes rouges transparentes là où le bus a planté."""
    for t in erreurs_bus:
        plt_obj.axvline(x=t, color='red', alpha=0.02, linewidth=1)

print("\nGénération des graphiques en cours...")

# =====================================================================
# GRAPHIQUE 1 : Éclairage Principal (Veilleuses & Antibrouillards)
# =====================================================================
plt.figure(figsize=(12, 4))
plt.step(bcm['Time'], bcm['Veill_Crois'], label='Veilleuses / Croisement', color='blue', linewidth=2)
plt.step(bcm['Time'], bcm['Antibrouillard'] + 1.5, label='Antibrouillards', color='cyan', linewidth=2)
ajouter_crash_bus(plt)
plt.title("Test 4 : Éclairage Principal (Lignes Rouges = Crash Bus)")
plt.xlabel("Temps (ms)")
plt.yticks([0, 1, 1.5, 2.5], ['Off', 'On', 'Off', 'On'])
plt.legend(loc='upper right')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("graph_01_eclairage_principal.png")
plt.close()

# =====================================================================
# GRAPHIQUE 2 : Signaux de Direction (Clignotants & Warning)
# =====================================================================
plt.figure(figsize=(12, 4))
plt.step(bcm['Time'], bcm['Cligno_G'], label='Cligno Gauche', color='gold', linewidth=1.5)
plt.step(bcm['Time'], bcm['Cligno_D'] + 1.5, label='Cligno Droit', color='darkorange', linewidth=1.5)
plt.step(bcm['Time'], bcm['Warning'] + 3.0, label='Warning (Détresse)', color='black', linewidth=2)
ajouter_crash_bus(plt)
plt.title("Test 4 : Signaux de Direction et Warning (Lignes Rouges = Crash Bus)")
plt.xlabel("Temps (ms)")
plt.yticks([0, 1, 1.5, 2.5, 3.0, 4.0], ['Off', 'On', 'Off', 'On', 'Off', 'On'])
plt.legend(loc='upper right')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("graph_02_direction.png")
plt.close()

# =====================================================================
# GRAPHIQUE 3 : Marche Arrière et Vitesse
# =====================================================================
plt.figure(figsize=(12, 4))
plt.step(bcm['Time'], bcm['Feu_Recul'], label='Feu de Recul (Marche Arrière)', color='purple', linewidth=2)
ajouter_crash_bus(plt)
plt.title("Test 4 : Engagement Marche Arrière (Lignes Rouges = Crash Bus)")
plt.xlabel("Temps (ms)")
plt.yticks([0, 1], ['Off', 'On'])
plt.legend(loc='upper right')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("graph_03_marche_arriere.png")
plt.close()

# =====================================================================
# GRAPHIQUE 4 : Pédale Physique (ABS) vs Ampoules Feux Stop (BCM)
# =====================================================================

plt.figure(figsize=(12, 4))
# On trace la pédale lue par l'ABS
plt.step(abs_data['Time'], abs_data['Pedale_Frein'], label='Capteur Pédale Frein (Input ABS)', color='green', linewidth=2)
# On trace l'allumage des ampoules décidé par le BCM (Légèrement décalé de +0.05 pour ne pas cacher la ligne verte)
plt.step(bcm['Time'], bcm['Feux_Stop'] + 0.05, label='Ampoules Feux Stop (Output BCM)', color='red', linestyle='--', linewidth=2)
ajouter_crash_bus(plt)
plt.title("Test 4 : Comparaison Pédale Physique vs Allumage des Feux Stop")
plt.xlabel("Temps (ms)")
plt.yticks([0, 1], ['Relâché / Éteint', 'Appuyé / Allumé'])
plt.legend(loc='center right')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("graph_04_freinage_comparatif.png")
plt.close()

# Sauvegarde globale CSV
df.to_csv('Audi_A3_Test4_Master_Analysis.csv', index=False)
print("Tout est terminé ! Les 4 graphiques et le fichier CSV ont été générés.")