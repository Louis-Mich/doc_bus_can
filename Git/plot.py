import matplotlib.pyplot as plt
import numpy as np

def generate_nc_plot(burst_bits, delay_e2e_us, rate_mbps):
    # Conversion des unités
    R = rate_mbps * 1e6      # 100 Mbps -> bits/s
    sigma = burst_bits       # bits
    delay_s = delay_e2e_us * 1e-6
    
    # Création de l'axe temps (jusqu'à 2 fois le délai pour bien voir)
    t = np.linspace(0, delay_s * 2, 1000)
    
    # Courbe d'arrivée cumulée A(t) - Modèle simple
    # On considère que le burst arrive à t=0
    arrivee = np.full_like(t, sigma)
    arrivee[t < 0] = 0 # Juste pour la forme
    
    # Courbe de service omega(t) - Rate Latency
    # On utilise le délai total pour décaler la pente
    latence_pure = delay_s - (sigma / R)
    service = np.maximum(0, R * (t - latence_pure))

    plt.figure(figsize=(10, 6))
    
    # Tracé des courbes
    plt.step(t * 1e6, arrivee, where='post', label='Arrivée Cumulée A(t)', color='#1f77b4', lw=2)
    plt.plot(t * 1e6, service, label='Service Garanti $\omega(t)$', color='#d62728', lw=2)

    # --- AJOUT DES FLÈCHES DE MESURE ---
    
    # 1. Flèche du Backlog (Verticale) au temps t_latence
    plt.annotate('', xy=(latence_pure * 1e6, sigma), xytext=(latence_pure * 1e6, 0),
                 arrowprops=dict(arrowstyle='<->', color='green', lw=2))
    plt.text(latence_pure * 1e6 - 15, sigma/2, f'Backlog max\n{sigma} bits', 
             color='green', fontweight='bold', ha='right', va='center')

    # 2. Flèche du Délai (Horizontale) au niveau du burst
    plt.annotate('', xy=(delay_s * 1e6, sigma), xytext=(0, sigma),
                 arrowprops=dict(arrowstyle='<->', color='orange', lw=2))
    plt.text((delay_s * 1e6)/2, sigma + (sigma*0.05), f'Délai max: {delay_e2e_us} µs', 
             color='orange', fontweight='bold', ha='center')

    # Mise en forme
    plt.title(f"Modélisation Network Calculus (Cas ESE.xml)", fontsize=14)
    plt.xlabel("Temps (µs)", fontsize=12)
    plt.ylabel("Données (bits)", fontsize=12)
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.legend(loc='lower right')
    plt.ylim(0, sigma * 1.5)
    plt.xlim(0, delay_s * 1.5 * 1e6)
    
    plt.tight_layout()
    plt.savefig("modelisation_backlog_delay.png", dpi=300)
    plt.show()

# Utilisation avec tes valeurs de ESE.xml
generate_nc_plot(burst_bits=8536, delay_e2e_us=179, rate_mbps=100)