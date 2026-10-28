/* Sonos Follow Me — bundled, dependency-free Home Assistant dashboard card. */
(async () => {
  // Extra frontend modules may execute before HA replaces customElements AND
  // HTMLElement with its scoped-registry polyfill. Check the CURRENT registry:
  // whenDefined() on the old registry would wait forever. Define classes only
  // after the app has installed the registry, including on YAML dashboards.
  while (!customElements.get("home-assistant")) {
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  // BEGIN GENERATED TRANSLATIONS
  const words = {
    de: {
      occupied: "Belegt",
      clear: "Frei",
      unavailable: "Nicht verfügbar",
      playing: "Wiedergabe",
      paused: "Pausiert",
      idle: "Bereit",
      on: "An",
      off: "Aus",
      empty:
        "Keine Follow-Me-Räume gefunden. Zuerst die Integration einrichten.",
      settings: "Einstellungen & Sensoren",
      remembered: "Letzte Lautstärke",
      target: "Ziel-Lautstärke",
      tv_volume_offset: "TV-Offset",
      tv_active: "TV-Lautstärke aktiv",
      cooldown_hint:
        "Nach Ablauf wird bei der nächsten Bewegung auf die Standardlautstärke eingeblendet, statt die zuletzt am Lautsprecher eingestellte Lautstärke zu übernehmen. Gilt bei aktivierter Option „Standardlautstärke verwenden“.",
      sources: "Musikquellen",
      sensors: "Sensoren",
      speaker: "Lautsprecher",
      error: "Änderung fehlgeschlagen",
      title: "Titel",
      choose: "Räume (ohne Auswahl: alle)",
      cooldown: "Abkühlzeit läuft",
      ready: "Standardlautstärke beim nächsten Besuch",
      minute: "min",
      resetHint: "0 Minuten = Standardlautstärke beim nächsten Besuch.",
      missing: "Raum nicht verfügbar",
      edit: "Raumzuordnung bearbeiten",
      room_count: {
        one: "{count} Raum",
        few: "{count} Räume",
        many: "{count} Räume",
        other: "{count} Räume",
      },
      invalid_entities:
        "entities muss eine Liste von Follow-Me-Schalter-Entitäts-IDs sein.",
      volume_mode: "Lautstärkequelle",
      room: "Eigene Raumlautstärke",
      group: "Gruppe folgen",
      master: "Master folgen",
      default_volume: "Standardlautstärke",
      volume_cooldown: "Abkühlzeit",
      off_delay: "Ausschaltverzögerung",
      fade_seconds: "Überblenddauer",
      volume_reset: "Standardlautstärke verwenden",
      mode: "Sensorlogik",
      primary: "Primär startet, weitere halten",
      equal: "Alle Sensoren gleichberechtigt",
      tv_hint:
        "Zur gewählten Ziel-Lautstärke addiert, auch beim Folgen von Gruppe oder Master. 30 % − 10 % = 20 %. 0 = deaktiviert. Musik/AirPlay bleiben unverändert.",
      follow_hint:
        "Gruppe: Durchschnitt der Quelllautsprecher ohne aktive Follow-Me-Ziele. Master: aktueller Gruppenkoordinator. Änderungen werden während der Belegung übernommen. Eigene Raumlautstärke: letzte Lautstärke oder Standard nach Abkühlzeit.",
    },
    en: {
      occupied: "Occupied",
      clear: "Clear",
      unavailable: "Unavailable",
      playing: "Playing",
      paused: "Paused",
      idle: "Idle",
      on: "On",
      off: "Off",
      empty: "No Follow Me rooms found. Set up the integration first.",
      settings: "Settings & sensors",
      remembered: "Remembered volume",
      target: "Target volume",
      tv_volume_offset: "TV offset",
      tv_active: "TV volume active",
      cooldown_hint:
        "After the cooldown, the next movement fades to the default volume instead of the last volume set on the speaker. Applies when “Use default volume” is enabled.",
      sources: "Music sources",
      sensors: "Sensors",
      speaker: "Speaker",
      error: "Change failed",
      title: "Title",
      choose: "Rooms (empty selection: all)",
      cooldown: "Cooldown running",
      ready: "Default volume on next visit",
      minute: "min",
      resetHint: "0 minutes = default volume on the next visit.",
      missing: "Room unavailable",
      edit: "Edit room assignment",
      room_count: {
        one: "{count} room",
        few: "{count} rooms",
        many: "{count} rooms",
        other: "{count} rooms",
      },
      invalid_entities:
        "entities must be a list of Follow Me switch entity IDs",
      volume_mode: "Volume source",
      room: "Own room volume",
      group: "Follow group",
      master: "Follow master",
      default_volume: "Default volume",
      volume_cooldown: "Volume cooldown",
      off_delay: "Clear delay",
      fade_seconds: "Fade duration",
      volume_reset: "Use default volume",
      mode: "Sensor mode",
      primary: "Primary starts, additional sensors hold",
      equal: "All sensors equal",
      tv_hint:
        "Added to the selected target volume, including when following the group or master. 30 % − 10 % = 20 %. 0 = disabled. Music/AirPlay are unchanged.",
      follow_hint:
        "Group: average source-speaker volume excluding active Follow Me destinations. Master: current group coordinator. Changes are followed while occupied. Own room volume: remembered volume or default after cooldown.",
    },
    es: {
      occupied: "Ocupada",
      clear: "Libre",
      unavailable: "No disponible",
      playing: "Reproduciendo",
      paused: "En pausa",
      idle: "Listo",
      on: "Encendido",
      off: "Apagado",
      empty:
        "No se han encontrado habitaciones Follow Me. Configura primero la integración.",
      settings: "Ajustes y sensores",
      remembered: "Último volumen",
      target: "Volumen objetivo",
      tv_volume_offset: "Ajuste de TV",
      tv_active: "Volumen de TV activo",
      cooldown_hint:
        "Al finalizar este tiempo, el siguiente movimiento inicia un fundido al volumen predeterminado, en lugar del último volumen ajustado en el altavoz. Se aplica si «Usar el volumen predeterminado» está activado.",
      sources: "Fuentes de música",
      sensors: "Sensores",
      speaker: "Altavoz",
      error: "No se pudo guardar el cambio",
      title: "Título",
      choose: "Habitaciones (sin selección: todas)",
      cooldown: "Restablecimiento pendiente",
      ready: "Volumen predeterminado en la próxima visita",
      minute: "min",
      resetHint: "0 minutos = volumen predeterminado en la próxima visita.",
      missing: "Habitación no disponible",
      edit: "Editar asignación de habitación",
      invalid_entities:
        "entities debe ser una lista de identificadores de entidades de interruptor Follow Me.",
      room_count: {
        one: "{count} habitación",
        few: "{count} habitaciones",
        many: "{count} habitaciones",
        other: "{count} habitaciones",
      },
      volume_mode: "Fuente del volumen",
      room: "Volumen propio de la habitación",
      group: "Seguir al grupo",
      master: "Seguir al coordinador",
      default_volume: "Volumen predeterminado",
      volume_cooldown: "Tiempo de restablecimiento",
      off_delay: "Retardo de ausencia",
      fade_seconds: "Duración del fundido",
      volume_reset: "Usar el volumen predeterminado",
      mode: "Lógica de sensores",
      primary: "El principal inicia, los demás mantienen",
      equal: "Todos los sensores son iguales",
      tv_hint:
        "Se suma al volumen objetivo seleccionado, incluso al seguir al grupo o al coordinador. 30 % − 10 % = 20 %. 0 = desactivado. La música y AirPlay no cambian.",
      follow_hint:
        "Grupo: volumen medio de los altavoces de origen, sin los destinos Follow Me activos. Coordinador: coordinador actual del grupo. Se siguen los cambios mientras la habitación está ocupada. Volumen propio: último volumen o valor predeterminado tras el tiempo de restablecimiento.",
    },
    fr: {
      occupied: "Occupée",
      clear: "Libre",
      unavailable: "Indisponible",
      playing: "Lecture",
      paused: "En pause",
      idle: "Prête",
      on: "Activé",
      off: "Désactivé",
      empty:
        "Aucune pièce Follow Me trouvée. Configurer d’abord l’intégration.",
      settings: "Réglages et capteurs",
      remembered: "Dernier volume",
      target: "Volume cible",
      tv_volume_offset: "Décalage TV",
      tv_active: "Volume TV actif",
      cooldown_hint:
        "Après ce délai, le prochain mouvement déclenche un fondu vers le volume par défaut au lieu du dernier volume réglé sur l’enceinte. S’applique lorsque « Utiliser le volume par défaut » est activé.",
      sources: "Sources musicales",
      sensors: "Capteurs",
      speaker: "Enceinte",
      error: "Échec de la modification",
      title: "Titre",
      choose: "Pièces (aucune sélection : toutes)",
      cooldown: "Réinitialisation en attente",
      ready: "Volume par défaut à la prochaine visite",
      minute: "min",
      resetHint: "0 minute = volume par défaut à la prochaine visite.",
      missing: "Pièce indisponible",
      edit: "Modifier l’affectation de la pièce",
      invalid_entities:
        "entities doit être une liste d’identifiants d’entités interrupteurs Follow Me.",
      room_count: {
        one: "{count} pièce",
        few: "{count} pièces",
        many: "{count} pièces",
        other: "{count} pièces",
      },
      volume_mode: "Source du volume",
      room: "Volume propre à la pièce",
      group: "Suivre le groupe",
      master: "Suivre le coordinateur",
      default_volume: "Volume par défaut",
      volume_cooldown: "Délai de réinitialisation",
      off_delay: "Délai avant absence",
      fade_seconds: "Durée du fondu",
      volume_reset: "Utiliser le volume par défaut",
      mode: "Logique des capteurs",
      primary: "Le principal déclenche, les autres maintiennent",
      equal: "Tous les capteurs sont équivalents",
      tv_hint:
        "Ajouté au volume cible sélectionné, même en suivant le groupe ou le coordinateur. 30 % − 10 % = 20 %. 0 = désactivé. La musique et AirPlay restent inchangés.",
      follow_hint:
        "Groupe : volume moyen des enceintes sources, sans les enceintes cibles Follow Me actives. Coordinateur : coordinateur actuel du groupe. Les changements sont suivis pendant la présence. Volume propre à la pièce : dernier volume ou volume par défaut après le délai de réinitialisation.",
    },
    it: {
      occupied: "Occupata",
      clear: "Libera",
      unavailable: "Non disponibile",
      playing: "In riproduzione",
      paused: "In pausa",
      idle: "Pronto",
      on: "Acceso",
      off: "Spento",
      empty:
        "Nessuna stanza Follow Me trovata. Configura prima l’integrazione.",
      settings: "Impostazioni e sensori",
      remembered: "Ultimo volume",
      target: "Volume di destinazione",
      tv_volume_offset: "Offset TV",
      tv_active: "Volume TV attivo",
      cooldown_hint:
        "Al termine di questo intervallo, il movimento successivo avvia una dissolvenza verso il volume predefinito, anziché l’ultimo volume impostato sull’altoparlante. Si applica se «Usa il volume predefinito» è attivo.",
      sources: "Sorgenti musicali",
      sensors: "Sensori",
      speaker: "Altoparlante",
      error: "Modifica non riuscita",
      title: "Titolo",
      choose: "Stanze (nessuna selezione: tutte)",
      cooldown: "Ripristino in attesa",
      ready: "Volume predefinito alla visita successiva",
      minute: "min",
      resetHint: "0 minuti = volume predefinito alla visita successiva.",
      missing: "Stanza non disponibile",
      edit: "Modifica assegnazione della stanza",
      invalid_entities:
        "entities deve essere un elenco di ID di entità interruttore Follow Me.",
      room_count: {
        one: "{count} stanza",
        few: "{count} stanze",
        many: "{count} stanze",
        other: "{count} stanze",
      },
      volume_mode: "Sorgente del volume",
      room: "Volume della stanza",
      group: "Segui il gruppo",
      master: "Segui il coordinatore",
      default_volume: "Volume predefinito",
      volume_cooldown: "Tempo di ripristino",
      off_delay: "Ritardo di assenza",
      fade_seconds: "Durata della dissolvenza",
      volume_reset: "Usa il volume predefinito",
      mode: "Logica dei sensori",
      primary: "Il primario avvia, gli altri mantengono",
      equal: "Tutti i sensori sono equivalenti",
      tv_hint:
        "Sommato al volume di destinazione selezionato, anche seguendo il gruppo o il coordinatore. 30 % − 10 % = 20 %. 0 = disattivato. Musica e AirPlay restano invariati.",
      follow_hint:
        "Gruppo: volume medio degli altoparlanti sorgente, escluse le destinazioni Follow Me attive. Coordinatore: coordinatore attuale del gruppo. Le variazioni vengono seguite durante la presenza. Volume della stanza: ultimo volume o valore predefinito dopo il tempo di ripristino.",
    },
    nl: {
      occupied: "Bezet",
      clear: "Vrij",
      unavailable: "Niet beschikbaar",
      playing: "Afspelen",
      paused: "Gepauzeerd",
      idle: "Gereed",
      on: "Aan",
      off: "Uit",
      empty: "Geen Follow Me-ruimtes gevonden. Stel eerst de integratie in.",
      settings: "Instellingen en sensoren",
      remembered: "Laatste volume",
      target: "Doelvolume",
      tv_volume_offset: "TV-aanpassing",
      tv_active: "TV-volume actief",
      cooldown_hint:
        "Na deze wachttijd verhoogt de volgende beweging het volume geleidelijk tot het standaardvolume, in plaats van het laatst op de luidspreker ingestelde volume. Geldt als ‘Standaardvolume gebruiken’ is ingeschakeld.",
      sources: "Muziekbronnen",
      sensors: "Sensoren",
      speaker: "Luidspreker",
      error: "Wijziging mislukt",
      title: "Titel",
      choose: "Ruimtes (geen selectie: alle)",
      cooldown: "Herstelwachttijd loopt",
      ready: "Standaardvolume bij volgend bezoek",
      minute: "min",
      resetHint: "0 minuten = standaardvolume bij het volgende bezoek.",
      missing: "Ruimte niet beschikbaar",
      edit: "Ruimtetoewijzing wijzigen",
      invalid_entities:
        "entities moet een lijst met entiteits-ID’s van Follow Me-schakelaars zijn.",
      room_count: {
        one: "{count} ruimte",
        few: "{count} ruimtes",
        many: "{count} ruimtes",
        other: "{count} ruimtes",
      },
      volume_mode: "Volumebron",
      room: "Eigen ruimtevolume",
      group: "Groep volgen",
      master: "Coördinator volgen",
      default_volume: "Standaardvolume",
      volume_cooldown: "Herstelwachttijd",
      off_delay: "Vertraging bij afwezigheid",
      fade_seconds: "Duur van de volumeovergang",
      volume_reset: "Standaardvolume gebruiken",
      mode: "Sensorlogica",
      primary: "Primair start, extra sensoren houden vast",
      equal: "Alle sensoren gelijkwaardig",
      tv_hint:
        "Opgeteld bij het gekozen doelvolume, ook bij het volgen van de groep of coördinator. 30 % − 10 % = 20 %. 0 = uitgeschakeld. Muziek en AirPlay blijven ongewijzigd.",
      follow_hint:
        "Groep: gemiddeld volume van de bronluidsprekers, zonder actieve Follow Me-doelluidsprekers. Coördinator: huidige groepscoördinator. Wijzigingen worden gevolgd tijdens bezetting. Eigen ruimtevolume: laatste volume of standaardvolume na de herstelwachttijd.",
    },
    pl: {
      occupied: "Zajęte",
      clear: "Wolne",
      unavailable: "Niedostępne",
      playing: "Odtwarzanie",
      paused: "Wstrzymano",
      idle: "Gotowy",
      on: "Wł.",
      off: "Wył.",
      empty:
        "Nie znaleziono pomieszczeń Follow Me. Najpierw skonfiguruj integrację.",
      settings: "Ustawienia i czujniki",
      remembered: "Ostatnia głośność",
      target: "Głośność docelowa",
      tv_volume_offset: "Korekta TV",
      tv_active: "Aktywna głośność TV",
      cooldown_hint:
        "Po upływie tego czasu następny ruch płynnie zwiększy głośność do wartości domyślnej, zamiast przywracać ostatnią głośność ustawioną na głośniku. Dotyczy włączonej opcji „Używaj głośności domyślnej”.",
      sources: "Źródła muzyki",
      sensors: "Czujniki",
      speaker: "Głośnik",
      error: "Zmiana nie powiodła się",
      title: "Tytuł",
      choose: "Pomieszczenia (brak wyboru: wszystkie)",
      cooldown: "Trwa czas przywracania",
      ready: "Głośność domyślna przy następnej wizycie",
      minute: "min",
      resetHint: "0 minut = głośność domyślna przy następnej wizycie.",
      missing: "Pomieszczenie niedostępne",
      edit: "Edytuj przypisanie pomieszczenia",
      invalid_entities:
        "entities musi być listą identyfikatorów encji przełączników Follow Me.",
      room_count: {
        one: "{count} pomieszczenie",
        few: "{count} pomieszczenia",
        many: "{count} pomieszczeń",
        other: "{count} pomieszczeń",
      },
      volume_mode: "Źródło głośności",
      room: "Własna głośność pomieszczenia",
      group: "Śledź grupę",
      master: "Śledź koordynatora",
      default_volume: "Głośność domyślna",
      volume_cooldown: "Czas przywracania",
      off_delay: "Opóźnienie nieobecności",
      fade_seconds: "Czas płynnej zmiany głośności",
      volume_reset: "Używaj głośności domyślnej",
      mode: "Logika czujników",
      primary: "Główny rozpoczyna, dodatkowe podtrzymują",
      equal: "Wszystkie czujniki równorzędne",
      tv_hint:
        "Dodawana do wybranej głośności docelowej, również przy śledzeniu grupy lub koordynatora. 30 % − 10 % = 20 %. 0 = wyłączona. Muzyka i AirPlay pozostają bez zmian.",
      follow_hint:
        "Grupa: średnia głośność głośników źródłowych, bez aktywnych głośników docelowych Follow Me. Koordynator: bieżący koordynator grupy. Zmiany są śledzone podczas obecności. Własna głośność pomieszczenia: ostatnia głośność lub domyślna po czasie przywracania.",
    },
    "pt-BR": {
      occupied: "Ocupado",
      clear: "Livre",
      unavailable: "Indisponível",
      playing: "Reproduzindo",
      paused: "Em pausa",
      idle: "Pronto",
      on: "Ligado",
      off: "Desligado",
      empty:
        "Nenhum cômodo Follow Me encontrado. Configure a integração primeiro.",
      settings: "Configurações e sensores",
      remembered: "Último volume",
      target: "Volume de destino",
      tv_volume_offset: "Ajuste de TV",
      tv_active: "Volume de TV ativo",
      cooldown_hint:
        "Após esse período, o próximo movimento inicia uma transição para o volume padrão, em vez do último volume definido no alto-falante. Aplica-se quando «Usar o volume padrão» está ativado.",
      sources: "Fontes de música",
      sensors: "Sensores",
      speaker: "Alto-falante",
      error: "Falha ao alterar",
      title: "Título",
      choose: "Cômodos (sem seleção: todos)",
      cooldown: "Restauração pendente",
      ready: "Volume padrão na próxima visita",
      minute: "min",
      resetHint: "0 minutos = volume padrão na próxima visita.",
      missing: "Cômodo indisponível",
      edit: "Editar atribuição do cômodo",
      invalid_entities:
        "entities deve ser uma lista de IDs de entidades de interruptor Follow Me.",
      room_count: {
        one: "{count} cômodo",
        few: "{count} cômodos",
        many: "{count} cômodos",
        other: "{count} cômodos",
      },
      volume_mode: "Origem do volume",
      room: "Volume próprio do cômodo",
      group: "Seguir o grupo",
      master: "Seguir o coordenador",
      default_volume: "Volume padrão",
      volume_cooldown: "Tempo de restauração",
      off_delay: "Atraso de ausência",
      fade_seconds: "Duração da transição",
      volume_reset: "Usar o volume padrão",
      mode: "Lógica dos sensores",
      primary: "O principal inicia, os adicionais mantêm",
      equal: "Todos os sensores são iguais",
      tv_hint:
        "Somado ao volume de destino selecionado, inclusive ao seguir o grupo ou o coordenador. 30 % − 10 % = 20 %. 0 = desativado. Música e AirPlay não são alterados.",
      follow_hint:
        "Grupo: volume médio dos alto-falantes de origem, sem os destinos Follow Me ativos. Coordenador: coordenador atual do grupo. As alterações são acompanhadas durante a ocupação. Volume próprio do cômodo: último volume ou volume padrão após o tempo de restauração.",
    },
    pt: {
      occupied: "Ocupada",
      clear: "Livre",
      unavailable: "Indisponível",
      playing: "A reproduzir",
      paused: "Em pausa",
      idle: "Pronta",
      on: "Ligado",
      off: "Desligado",
      empty:
        "Não foram encontradas divisões Follow Me. Configure primeiro a integração.",
      settings: "Definições e sensores",
      remembered: "Último volume",
      target: "Volume de destino",
      tv_volume_offset: "Ajuste TV",
      tv_active: "Volume TV ativo",
      cooldown_hint:
        "Após este período, o próximo movimento inicia uma transição para o volume predefinido, em vez do último volume definido na coluna. Aplica-se quando «Utilizar o volume predefinido» está ativo.",
      sources: "Fontes de música",
      sensors: "Sensores",
      speaker: "Coluna",
      error: "Falha ao alterar",
      title: "Título",
      choose: "Divisões (sem seleção: todas)",
      cooldown: "Reposição em espera",
      ready: "Volume predefinido na próxima visita",
      minute: "min",
      resetHint: "0 minutos = volume predefinido na próxima visita.",
      missing: "Divisão indisponível",
      edit: "Editar atribuição da divisão",
      invalid_entities:
        "entities tem de ser uma lista de identificadores de entidades de interruptor Follow Me.",
      room_count: {
        one: "{count} divisão",
        few: "{count} divisões",
        many: "{count} divisões",
        other: "{count} divisões",
      },
      volume_mode: "Origem do volume",
      room: "Volume próprio da divisão",
      group: "Seguir o grupo",
      master: "Seguir o coordenador",
      default_volume: "Volume predefinido",
      volume_cooldown: "Tempo de reposição",
      off_delay: "Atraso de ausência",
      fade_seconds: "Duração da transição",
      volume_reset: "Utilizar o volume predefinido",
      mode: "Lógica dos sensores",
      primary: "O principal inicia, os adicionais mantêm",
      equal: "Todos os sensores são iguais",
      tv_hint:
        "Somado ao volume de destino selecionado, incluindo ao seguir o grupo ou o coordenador. 30 % − 10 % = 20 %. 0 = desativado. A música e o AirPlay não são alterados.",
      follow_hint:
        "Grupo: volume médio das colunas de origem, excluindo destinos Follow Me ativos. Coordenador: coordenador atual do grupo. As alterações são seguidas durante a ocupação. Volume próprio da divisão: último volume ou volume predefinido após o tempo de reposição.",
    },
    sv: {
      occupied: "Upptaget",
      clear: "Ledigt",
      unavailable: "Inte tillgänglig",
      playing: "Spelar",
      paused: "Pausad",
      idle: "Redo",
      on: "På",
      off: "Av",
      empty: "Inga Follow Me-rum hittades. Konfigurera integrationen först.",
      settings: "Inställningar och sensorer",
      remembered: "Senaste volym",
      target: "Målvolym",
      tv_volume_offset: "TV-justering",
      tv_active: "TV-volym aktiv",
      cooldown_hint:
        "När tiden har löpt ut tonas volymen vid nästa rörelse upp till standardvolymen i stället för den senast inställda volymen på högtalaren. Gäller när ”Använd standardvolym” är aktiverat.",
      sources: "Musikkällor",
      sensors: "Sensorer",
      speaker: "Högtalare",
      error: "Ändringen misslyckades",
      title: "Titel",
      choose: "Rum (inget valt: alla)",
      cooldown: "Återställningstid pågår",
      ready: "Standardvolym vid nästa besök",
      minute: "min",
      resetHint: "0 minuter = standardvolym vid nästa besök.",
      missing: "Rummet är inte tillgängligt",
      edit: "Redigera rumstilldelning",
      invalid_entities:
        "entities måste vara en lista med entitets-ID:n för Follow Me-brytare.",
      room_count: {
        one: "{count} rum",
        few: "{count} rum",
        many: "{count} rum",
        other: "{count} rum",
      },
      volume_mode: "Volymkälla",
      room: "Egen rumsvolym",
      group: "Följ gruppen",
      master: "Följ samordnaren",
      default_volume: "Standardvolym",
      volume_cooldown: "Återställningstid",
      off_delay: "Frånvarofördröjning",
      fade_seconds: "Toningstid",
      volume_reset: "Använd standardvolym",
      mode: "Sensorlogik",
      primary: "Primär aktiverar, övriga håller kvar",
      equal: "Alla sensorer är likvärdiga",
      tv_hint:
        "Läggs till den valda målvolymen, även när gruppen eller samordnaren följs. 30 % − 10 % = 20 %. 0 = inaktiverad. Musik och AirPlay påverkas inte.",
      follow_hint:
        "Grupp: medelvolymen för källhögtalarna, utan aktiva Follow Me-målhögtalare. Samordnare: gruppens nuvarande samordnare. Ändringar följs under närvaro. Egen rumsvolym: senaste volymen eller standardvolymen efter återställningstiden.",
    },
  };
  // END GENERATED TRANSLATIONS
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const valid = (state) =>
    state && !["unknown", "unavailable"].includes(state.state);
  const roomSwitches = (hass) =>
    Object.values(hass?.states || {}).filter(
      (s) =>
        s.entity_id.startsWith("switch.") &&
        s.attributes.sonos_follow_me_room &&
        s.attributes.setting === "enabled",
    );
  const language = (hass) => {
    const requested = (hass?.locale?.language || hass?.language || "en")
      .replaceAll("_", "-")
      .toLowerCase();
    return (
      Object.keys(words).find((key) => key.toLowerCase() === requested) ||
      (words[requested.split("-")[0]] ? requested.split("-")[0] : "en")
    );
  };
  const lang = (hass) => words[language(hass)];
  const roomCount = (count, hass) => {
    const forms = lang(hass).room_count;
    const form = new Intl.PluralRules(language(hass)).select(count);
    return (forms[form] || forms.other).replace("{count}", String(count));
  };
  const css = `
:host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,system-ui)}
ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,16px);border:1px solid var(--divider-color,#ddd)}
.brand{display:flex;align-items:center;gap:10px;min-width:0}.logo{width:48px;height:48px;object-fit:contain;flex-shrink:0}.count{white-space:nowrap;flex-shrink:0}header{gap:12px;padding:20px 20px 12px;display:flex;justify-content:space-between;align-items:center}h2{overflow-wrap:anywhere;font-size:21px;margin:0;font-weight:600}.count,.muted{color:var(--secondary-text-color,#666);font-size:13px}.rooms{padding:0 12px 12px;display:grid;gap:10px}.room{border:1px solid var(--divider-color,#ddd);border-radius:12px;padding:16px;min-width:0}.heading{display:flex;align-items:center;gap:10px;justify-content:space-between}.name{font-size:17px;font-weight:600;overflow-wrap:anywhere}.badge{display:inline-block;border-radius:20px;padding:4px 9px;font-size:12px;background:var(--secondary-background-color,#f3f4f5);margin-top:8px}.occupied{color:var(--primary-color,#007c83);background:color-mix(in srgb,var(--primary-color,#007c83) 12%,transparent)}.summary{white-space:pre-line;margin:12px 0;font-size:13px;line-height:1.7;overflow-wrap:anywhere}.row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0;font-size:14px}input,select,button{font:inherit;color:inherit}input[type=checkbox]{width:22px;height:22px;accent-color:var(--primary-color,#007c83);cursor:pointer;flex-shrink:0}input[type=number],select{background:var(--secondary-background-color,#f6f7f8);border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:9px;box-sizing:border-box;max-width:100%;min-width:0}input[type=number]{width:100%}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}.field{display:grid;gap:6px;font-size:12px;color:var(--secondary-text-color,#666)}.field input{color:var(--primary-text-color)}details{border-top:1px solid var(--divider-color,#ddd);margin-top:14px;padding-top:12px}summary{cursor:pointer;font-size:14px;font-weight:500;padding:4px 0}select{width:100%;margin-top:6px}ul{padding-left:18px;font-size:13px;line-height:1.7;overflow-wrap:anywhere}.error{padding:12px;color:var(--error-color,#b00020);overflow-wrap:anywhere}.empty{padding:20px}.hint{font-size:12px;line-height:1.5;color:var(--secondary-text-color,#666);margin-top:12px}a{color:var(--primary-color,#007c83);font-size:13px}input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--primary-color,#007c83);outline-offset:3px}:disabled{opacity:.5;cursor:not-allowed}
`;
  const sliderCss = `
.slider-field,.cooldown-field{grid-column:1/-1}
.field-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}
.field-value{font-size:15px;font-weight:600;color:var(--primary-text-color);font-variant-numeric:tabular-nums;white-space:nowrap}
input[type=range]{width:100%;min-width:0;min-height:36px;margin:0;accent-color:var(--primary-color,#007c83);cursor:pointer}
.field .hint{margin:0}.cooldown-field input{max-width:140px}
`;

  class SonosFollowMeCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._expanded = new Set();
      this._busy = new Set();
      this.shadowRoot.addEventListener("focusout", () =>
        setTimeout(() => this._render(), 0),
      );
    }
    setConfig(config) {
      if (
        config.entities !== undefined &&
        (!Array.isArray(config.entities) ||
          config.entities.some(
            (e) => typeof e !== "string" || !e.startsWith("switch."),
          ))
      )
        throw new Error(lang(this._hass).invalid_entities);
      this._config = { ...config };
      this._render();
    }
    set hass(hass) {
      const modes = Object.values(hass.states)
        .filter((s) => s.attributes.setting === "volume_mode")
        .map((s) => `${s.entity_id}:${s.state}`)
        .sort()
        .join("|");
      const changed =
        modes !== this._volumeModes || language(hass) !== this._language;
      this._language = language(hass);
      this._volumeModes = modes;
      this._hass = hass;
      this._render(changed);
    }
    connectedCallback() {
      if (!this._interval)
        this._interval = setInterval(() => this._render(), 30000);
    }
    disconnectedCallback() {
      clearInterval(this._interval);
      this._interval = null;
    }
    static getStubConfig() {
      return { type: "custom:sonos-follow-me-card", title: "Sonos Follow Me" };
    }
    static getConfigElement() {
      return document.createElement("sonos-follow-me-card-editor");
    }
    getCardSize() {
      return (
        2 +
        6 *
          (this._config?.entities?.length ||
            roomSwitches(this._hass).length ||
            1)
      );
    }
    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }
    async _call(state, action, data = {}) {
      if (!state || this._busy.has(state.entity_id)) return;
      const id = state.entity_id;
      this._busy.add(id);
      this._error = "";
      this._render(true);
      try {
        await this._hass.callService(id.split(".")[0], action, {
          entity_id: id,
          ...data,
        });
      } catch (error) {
        this._error = `${lang(this._hass).error}: ${error.message || error}`;
      } finally {
        this._busy.delete(id);
        this._render(true);
      }
    }
    _toggle(state, text, parent) {
      const label = node("label", undefined, "row");
      label.append(node("span", text));
      const input = node("input");
      input.type = "checkbox";
      input.checked = state?.state === "on";
      input.setAttribute("aria-label", text);
      input.disabled = !valid(state) || this._busy.has(state.entity_id);
      input.addEventListener("change", () =>
        this._call(state, input.checked ? "turn_on" : "turn_off"),
      );
      label.append(input);
      parent.append(label);
    }
    _select(state, key, options, parent, t) {
      if (!state) return;
      const label = node("label", t[key], "field");
      const select = node("select");
      select.setAttribute("aria-label", t[key]);
      for (const option of options) {
        const el = node("option", t[option]);
        el.value = option;
        select.append(el);
      }
      select.value = state.state;
      select.disabled = !valid(state) || this._busy.has(state.entity_id);
      select.addEventListener("change", () =>
        this._call(state, "select_option", { option: select.value }),
      );
      label.append(select);
      parent.append(label);
    }
    _number(state, key, parent, t) {
      if (!state) return;
      const label = node("label", undefined, "field");
      const slider = ["default_volume", "tv_volume_offset"].includes(key);
      const unit = slider ? "%" : state.attributes.unit_of_measurement || "";
      const heading = node("span", undefined, "field-heading");
      heading.append(node("span", `${t[key]} (${unit})`));
      label.append(heading);
      const input = node("input");
      input.type = slider ? "range" : "number";
      input.min = state.attributes.min;
      input.max = state.attributes.max;
      input.step = state.attributes.step;
      input.value = valid(state) ? state.state : slider ? "0" : "";
      input.setAttribute("aria-label", t[key]);
      input.disabled = !valid(state) || this._busy.has(state.entity_id);
      if (slider) {
        label.classList.add("slider-field");
        input.dataset.sliderEntity = state.entity_id;
        const value = node("span", undefined, "field-value");
        const updateValue = () => {
          const number = Number(input.value);
          value.textContent = valid(this._hass.states[state.entity_id])
            ? `${key === "tv_volume_offset" && number > 0 ? "+" : ""}${number} %`
            : "—";
          input.setAttribute("aria-valuetext", value.textContent);
        };
        updateValue();
        input.addEventListener("input", updateValue);
        input.addEventListener("pointerdown", () => {
          this._sliding = true;
          const released = () => {
            this._sliding = false;
            window.removeEventListener("pointerup", released);
            window.removeEventListener("pointercancel", released);
          };
          window.addEventListener("pointerup", released);
          window.addEventListener("pointercancel", released);
        });
        heading.append(value);
      }
      input.addEventListener("change", async () => {
        if (input.value === "" || !input.reportValidity()) return;
        // Keep keyboard adjustment usable after the state update rebuilds the card.
        let restoreFocus = slider && this.shadowRoot.activeElement === input;
        const focusMoved = () => {
          restoreFocus = false;
        };
        document.addEventListener("focusin", focusMoved);
        try {
          await this._call(state, "set_value", { value: Number(input.value) });
        } finally {
          document.removeEventListener("focusin", focusMoved);
          if (restoreFocus)
            [...this.shadowRoot.querySelectorAll("input[type=range]")]
              .find(
                (element) => element.dataset.sliderEntity === state.entity_id,
              )
              ?.focus({ preventScroll: true });
        }
      });
      label.append(input);
      if (key === "volume_cooldown" || key === "tv_volume_offset") {
        const hint = node(
          "span",
          t[key === "volume_cooldown" ? "cooldown_hint" : "tv_hint"],
          "hint",
        );
        hint.id = `${state.entity_id}-hint`;
        input.setAttribute("aria-describedby", hint.id);
        label.append(hint);
        if (key === "volume_cooldown") label.classList.add("cooldown-field");
      }
      parent.append(label);
    }
    _render(force = false) {
      if (!this._hass || !this._config) return;
      const active = this.shadowRoot.activeElement;
      if (!force && active) {
        const id = active.dataset.sliderEntity;
        // HA may deliver the authoritative state after the service promise resolves.
        // Refresh an idle focused slider without replacing it or interrupting a drag.
        if (id && !this._sliding && !this._busy.has(id)) {
          const current = this._hass.states[id];
          active.value = valid(current) ? current.state : "0";
          active.disabled = !valid(current);
          active.dispatchEvent(new Event("input"));
        }
        return;
      }
      const hass = this._hass,
        t = lang(hass),
        states = Object.values(hass.states);
      const switches = this._config.entities?.length
        ? this._config.entities.map((id) => hass.states[id])
        : roomSwitches(hass).sort((a, b) =>
            (a.attributes.room_name || "").localeCompare(
              b.attributes.room_name || "",
            ),
          );
      // Keep the image and header connected across HA state updates and service calls.
      // Recreating the image on every render restarts loading/decoding and visibly flashes.
      if (!this._card) {
        this._card = node("ha-card");
        const header = node("header"),
          brand = node("div", undefined, "brand");
        const logo = node("img", undefined, "logo");
        logo.src = "/sonos_follow_me/follow-me-logo.png?v=0.4.0";
        logo.alt = "";
        logo.width = 48;
        logo.height = 48;
        this._title = node("h2");
        this._count = node("span", undefined, "count");
        brand.append(logo, this._title);
        header.append(brand, this._count);
        this._errorElement = node("div", undefined, "error");
        this._errorElement.setAttribute("role", "alert");
        this._rooms = node("div", undefined, "rooms");
        this._card.append(header, this._errorElement, this._rooms);
        this.shadowRoot.append(node("style", css + sliderCss), this._card);
      }
      this._title.textContent = this._config.title || "Sonos Follow Me";
      this._count.textContent = roomCount(switches.length, hass);
      this._errorElement.textContent = this._error || "";
      this._errorElement.hidden = !this._error;
      const container = document.createDocumentFragment();
      if (!switches.length) container.append(node("div", t.empty, "empty"));
      for (const enabled of switches) {
        if (
          !enabled?.attributes.sonos_follow_me_room ||
          enabled.attributes.setting !== "enabled"
        ) {
          container.append(node("div", t.missing, "empty"));
          continue;
        }
        const a = enabled.attributes,
          id = a.sonos_follow_me_room;
        const settings = Object.fromEntries(
          states
            .filter((s) => s.attributes.sonos_follow_me_room === id)
            .map((s) => [s.attributes.setting, s]),
        );
        const room = node("section", undefined, "room");
        room.dataset.room = id;
        const heading = node("div", undefined, "heading");
        heading.append(
          node("div", a.room_name || enabled.attributes.friendly_name, "name"),
        );
        this._toggle(enabled, "Follow Me", heading);
        room.append(heading);
        const occupancy = settings.occupancy;
        room.append(
          node(
            "span",
            !valid(occupancy)
              ? t.unavailable
              : occupancy.state === "on"
                ? t.occupied
                : t.clear,
            `badge ${occupancy?.state === "on" ? "occupied" : ""}`,
          ),
        );
        const player = hass.states[a.player];
        const following =
          (settings.volume_mode?.state || a.volume_mode || "room") !== "room";
        const friendly = (entity) =>
          hass.states[entity]?.attributes.friendly_name || entity;
        room.append(
          node(
            "div",
            `${t.speaker}: ${friendly(a.player)} · ${t[player?.state] || player?.state || t.unavailable}\n${following ? t.target : t.remembered}: ${Math.round((following ? a.playback_target_volume || 0 : a.remembered_volume || 0) * 100)} %`,
            "summary",
          ),
        );
        this._select(
          settings.volume_mode,
          "volume_mode",
          ["room", "group", "master"],
          room,
          t,
        );
        if (!following)
          this._toggle(settings.volume_reset, t.volume_reset, room);
        const grid = node("div", undefined, "grid");
        for (const key of following
          ? ["tv_volume_offset"]
          : ["default_volume", "tv_volume_offset", "volume_cooldown"])
          this._number(settings[key], key, grid, t);
        room.append(grid);
        if (a.tv_volume_active)
          room.append(
            node(
              "div",
              `${t.tv_active}: ${Math.round(a.playback_target_volume * 100)} %`,
              "badge occupied",
            ),
          );
        if (
          !following &&
          settings.volume_reset?.state === "on" &&
          a.vacant_since != null &&
          valid(settings.volume_cooldown)
        ) {
          const left = Math.max(
            0,
            Math.ceil(
              (Number(a.vacant_since) +
                Number(settings.volume_cooldown.state) * 60 -
                Date.now() / 1000) /
                60,
            ),
          );
          room.append(
            node(
              "div",
              left ? `${t.cooldown}: ${left} ${t.minute}` : t.ready,
              "hint",
            ),
          );
        } else
          room.append(
            node("div", following ? t.follow_hint : t.resetHint, "hint"),
          );
        const details = node("details");
        details.open = this._expanded.has(id);
        details.append(node("summary", t.settings));
        details.addEventListener("toggle", () => {
          if (details.open) this._expanded.add(id);
          else this._expanded.delete(id);
        });
        const more = node("div", undefined, "grid");
        for (const key of ["off_delay", "fade_seconds"])
          this._number(settings[key], key, more, t);
        details.append(more);
        const mode = settings.mode;
        if (mode) {
          const label = node("label", t.mode, "field");
          const select = node("select");
          select.setAttribute("aria-label", t.mode);
          for (const option of ["primary", "equal"]) {
            const el = node("option", t[option]);
            el.value = option;
            select.append(el);
          }
          select.value = mode.state;
          select.disabled = !valid(mode) || this._busy.has(mode.entity_id);
          select.addEventListener("change", () =>
            this._call(mode, "select_option", { option: select.value }),
          );
          label.append(select);
          details.append(label);
        }
        details.append(node("p", t.sensors, "muted"));
        const sensors = node("ul");
        for (const entity of [a.primary, ...(a.secondary || [])].filter(
          Boolean,
        )) {
          const s = hass.states[entity];
          sensors.append(
            node(
              "li",
              `${friendly(entity)}: ${valid(s) ? (s.state === "on" ? t.occupied : t.clear) : t.unavailable}`,
            ),
          );
        }
        details.append(sensors);
        details.append(node("p", t.sources, "muted"));
        const sources = node("ol");
        sources.className = "muted";
        for (const source of a.sources || [])
          sources.append(node("li", friendly(source)));
        details.append(sources);
        const link = node("a", t.edit);
        link.href = "/config/integrations/integration/sonos_follow_me";
        details.append(link);
        room.append(details);
        container.append(room);
      }
      this._rooms.replaceChildren(container);
    }
  }

  class SonosFollowMeEditor extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
    }
    setConfig(config) {
      this._config = { ...config };
      this._render();
    }
    set hass(hass) {
      const changed = language(hass) !== this._language;
      this._language = language(hass);
      this._hass = hass;
      if (changed || !this.shadowRoot.activeElement) this._render();
    }
    _render() {
      if (!this._config || !this._hass) return;
      const t = lang(this._hass);
      this.shadowRoot.replaceChildren(node("style", css));
      const titleLabel = node("label", t.title, "field"),
        title = node("input");
      title.type = "text";
      title.value = this._config.title || "";
      title.setAttribute("aria-label", t.title);
      title.addEventListener("change", () =>
        this._emit({ ...this._config, title: title.value }),
      );
      titleLabel.append(title);
      this.shadowRoot.append(titleLabel, node("p", t.choose));
      const selected = this._config.entities || [];
      for (const room of roomSwitches(this._hass)) {
        const label = node("label", undefined, "row"),
          input = node("input");
        input.type = "checkbox";
        input.checked = selected.includes(room.entity_id);
        label.append(
          node("span", room.attributes.room_name || room.entity_id),
          input,
        );
        input.addEventListener("change", () => {
          const ids = new Set(this._config.entities || []);
          input.checked ? ids.add(room.entity_id) : ids.delete(room.entity_id);
          this._emit({ ...this._config, entities: [...ids] });
        });
        this.shadowRoot.append(label);
      }
    }
    _emit(config) {
      this._config = config;
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config },
          bubbles: true,
          composed: true,
        }),
      );
    }
  }
  if (!customElements.get("sonos-follow-me-card"))
    customElements.define("sonos-follow-me-card", SonosFollowMeCard);
  if (!customElements.get("sonos-follow-me-card-editor"))
    customElements.define("sonos-follow-me-card-editor", SonosFollowMeEditor);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === "sonos-follow-me-card"))
    window.customCards.push({
      type: "sonos-follow-me-card",
      name: "Sonos Follow Me",
      description: "Follow Me rooms, presence and volume settings",
      preview: true,
    });
})();
