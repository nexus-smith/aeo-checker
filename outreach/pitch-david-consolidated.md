# Pitch David — Consolidated (prêt à envoyer)

## Email

**Subject:** [Info] AEO Checker — où on en est + 3 quick wins pour Beesy

Salut David,

Suite à ta question "c'est quoi AEO ?", j'ai pris du recul pour remettre les choses à plat.

**AEO Checker en 1 phrase :** c'est un outil gratuit qui scanne n'importe quel site et te dit s'il est visible par les assistants IA (ChatGPT, Claude, Perplexity). Score sur 110, avec des recommandations concrètes.

**Ce qui existe aujourd'hui :**
- L'outil tourne, gratuit, accessible ici : https://extensions-tags-administered-fighter.trycloudflare.com
- 18 articles de blog (guides, études de cas, données)
- On a scanné 20 grosses boîtes tech — résultat moyen : 57/110. Sentry mène à 88, OpenAI est à 23 (oui, ironique)
- Notre propre site score 102/110

**J'ai scanné beesy.me : 25/110 (Mauvais).**

Le problème est simple : le fichier robots.txt de Beesy bloque TOUS les agents IA — ChatGPT, Claude, Perplexity, et même Google Search. Quand un client potentiel demande à une IA "quel outil pour gérer mes réunions ?", Beesy n'apparaît pas. L'IA ne peut même pas lire le site.

En plus, beesy.fr a un problème de certificat SSL — le site ne charge pas du tout.

C'est un réglage Cloudflare (tableau de bord → Security → Bots → AI Scrapers). JC peut corriger ça en 30 secondes. J'ai aussi préparé un fichier llms.txt (une sorte de CV du produit pour les IA) prêt à uploader.

**3 actions concrètes (30 min max le tout) :**
1. Désactiver le blocage IA dans Cloudflare → score passe de 25 à ~45
2. Uploader le fichier llms.txt que j'ai préparé → score passe à ~60
3. Corriger le certificat SSL de beesy.fr → le site français redevient accessible

**Pour le reste :**
- Les emails CEVA sont prêts depuis le 3 mars (tu avais dit "bravo"). Je propose de les envoyer lundi. Oui/Non ?
- J'ai un post Hacker News rédigé avec les données du scan des 20 boîtes tech. Tu cliques "submit", ça prend 30 secondes. Potentiellement gros trafic.

Dis-moi par quoi tu veux commencer.

— Nexus
