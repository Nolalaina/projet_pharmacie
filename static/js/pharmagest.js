document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".pg-sidebar");
  const boutonsSidebar = document.querySelectorAll("[data-sidebar-toggle]");

  const fermerSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.remove("show");
    boutonsSidebar.forEach((bouton) => bouton.setAttribute("aria-expanded", "false"));
  };

  boutonsSidebar.forEach((bouton) => {
    bouton.addEventListener("click", () => {
      if (!sidebar) return;
      const ouvert = sidebar.classList.toggle("show");
      boutonsSidebar.forEach((b) => b.setAttribute("aria-expanded", ouvert ? "true" : "false"));
    });
  });

  if (sidebar) {
    sidebar.querySelectorAll(".pg-nav-link, .pg-side-cta").forEach((lien) => {
      lien.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 991.98px)").matches) fermerSidebar();
      });
    });
  }

  document.addEventListener("keydown", (evenement) => {
    if (evenement.key === "Escape") fermerSidebar();
  });

  document.querySelectorAll("form[data-confirm]").forEach((formulaire) => {
    formulaire.addEventListener("submit", (evenement) => {
      if (!window.confirm(formulaire.dataset.confirm)) {
        evenement.preventDefault();
      }
    });
  });

  document.querySelectorAll("form[data-confirm-msg]").forEach((formulaire) => {
    formulaire.addEventListener("submit", (evenement) => {
      const message = formulaire.dataset.confirmMsg || "Êtes-vous sûr ?";
      if (!window.confirm(message)) {
        evenement.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-confirm-link]").forEach((element) => {
    element.addEventListener("click", (evenement) => {
      const message = element.dataset.confirmMsg || "Êtes-vous sûr de vouloir supprimer ?";
      if (!window.confirm(message)) {
        evenement.preventDefault();
      }
    });
  });

  const formatMontant = (valeur) =>
    new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(valeur || 0) + " Ar";

  document.querySelectorAll("[data-formset]").forEach((conteneur) => {
    const tbody = conteneur.querySelector("[data-formset-body]");
    const gabarit = conteneur.querySelector("template[data-formset-empty]");
    const total = conteneur.querySelector('input[name$="-TOTAL_FORMS"]');
    const ajouter = conteneur.querySelector("[data-add-row]");
    const prefixe = conteneur.dataset.prefix || "form";

    const activerLigne = (ligne) => {
      const retirer = ligne.querySelector("[data-remove-row]");
      if (retirer) {
        retirer.addEventListener("click", () => {
          const suppression = ligne.querySelector(
            'input[type="checkbox"][name$="-DELETE"]'
          );
          if (suppression) {
            suppression.checked = true;
          }
          const quantite =
            ligne.querySelector("[data-qte]") ||
            ligne.querySelector('input[name$="-quantite_commandee"]') ||
            ligne.querySelector('input[name$="-quantite"]');
          if (quantite) {
            quantite.value = "";
          }
          ligne.style.display = "none";
          maj();
        });
      }

      const selectLot =
        ligne.querySelector("[data-lot-select]") ||
        ligne.querySelector('select[name$="-lot"]');
      const quantite =
        ligne.querySelector("[data-qte]") ||
        ligne.querySelector('input[name$="-quantite_commandee"]') ||
        ligne.querySelector('input[name$="-quantite"]');
      if (selectLot) {
        selectLot.addEventListener("change", () => {
          const option = selectLot.selectedOptions[0];
          const prix = parseFloat(option?.dataset?.prix || "0");
          const stock = parseInt(option?.dataset?.stock || "0", 10);
          const cellulePrix = ligne.querySelector("[data-prix-cell]");
          if (cellulePrix) {
            cellulePrix.textContent = prix ? formatMontant(prix) : "—";
          }
          if (quantite) {
            if (stock) {
              quantite.max = stock;
            } else {
              quantite.removeAttribute("max");
            }
          }
          maj();
        });
      }

      ligne.querySelectorAll("input, select").forEach((champ) => {
        champ.addEventListener("input", maj);
        champ.addEventListener("change", maj);
      });

      maj();
    };

    const lignes = () => Array.from(tbody.querySelectorAll("tr"));

    const maj = () => {
      let sousTotal = 0;
      lignes().forEach((ligne) => {
        if (ligne.style.display === "none") {
          return;
        }
        const selectLot =
          ligne.querySelector("[data-lot-select]") ||
          ligne.querySelector('select[name$="-lot"]');
        const quantite =
          ligne.querySelector("[data-qte]") ||
          ligne.querySelector('input[name$="-quantite_commandee"]') ||
          ligne.querySelector('input[name$="-quantite"]');
        const prixAchat =
          ligne.querySelector("[data-prix-achat]") ||
          ligne.querySelector('input[name$="-prix_achat"]');
        const celluleTotal = ligne.querySelector("[data-line-total]");
        let prix = 0;
        if (selectLot) {
          const option = selectLot.selectedOptions[0];
          prix = parseFloat(option?.dataset?.prix || "0");
        } else if (prixAchat) {
          prix = parseFloat(prixAchat.value || "0");
        }
        const nombre = parseInt(quantite?.value || "0", 10);
        const totalLigne = prix * (isNaN(nombre) ? 0 : nombre);
        if (celluleTotal) {
          celluleTotal.textContent = totalLigne ? formatMontant(totalLigne) : "—";
        }
        sousTotal += totalLigne;
      });

      const champSousTotal = document.querySelector("[data-sous-total]");
      const champRemise =
        document.querySelector("[data-remise]") ||
        document.querySelector('input[name="remise"]');
      const champTotal = document.querySelector("[data-total-general]");
      const champRemiseAffichage = document.querySelector("[data-remise-affichage]");
      const remise = parseFloat(champRemise?.value || "0");
      if (champSousTotal) {
        champSousTotal.textContent = formatMontant(sousTotal);
      }
      if (champRemiseAffichage) {
        champRemiseAffichage.textContent = formatMontant(remise);
      }
      if (champTotal) {
        champTotal.textContent = formatMontant(Math.max(sousTotal - remise, 0));
      }
    };

    lignes().forEach(activerLigne);
    conteneur.addEventListener("pg:recalcul", maj);

    if (ajouter && gabarit && total) {
      ajouter.addEventListener("click", () => {
        const index = parseInt(total.value, 10);
        const html = gabarit.innerHTML.replaceAll("__prefix__", index);
        tbody.insertAdjacentHTML("beforeend", html);
        total.value = index + 1;
        activerLigne(tbody.lastElementChild);
      });
    }

    maj();
  });

  const champScan = document.querySelector("[data-scan-code]");
  if (champScan) {
    const conteneur = document.querySelector("[data-formset]");
    const tbody = conteneur?.querySelector("[data-formset-body]");
    const ajouterLigne = conteneur?.querySelector("[data-add-row]");
    const aide = document.querySelector("[data-scan-aide]");

    const signaler = (texte, erreur = false) => {
      if (!aide) return;
      aide.textContent = texte;
      aide.classList.toggle("text-danger", erreur);
      aide.classList.remove("text-success");
      aide.classList.add(erreur ? "text-danger" : "text-success");
    };

    const traiterScan = () => {
      const recherche = champScan.value.trim().toLowerCase();
      if (!recherche || !tbody) return;
      const options = Array.from(
        tbody.querySelectorAll('select[name$="-lot"] option')
      ).filter((option) => option.value);
      const cible =
        options.find(
          (option) => (option.dataset.code || "").toLowerCase() === recherche
        ) ||
        options.find((option) =>
          option.textContent.toLowerCase().includes(recherche)
        );
      if (!cible) {
        signaler("Aucun lot disponible ne correspond à cette recherche.", true);
        return;
      }

      let select = Array.from(
        tbody.querySelectorAll('select[name$="-lot"]')
      ).find((champ) => !champ.value);
      if (!select && ajouterLigne) {
        ajouterLigne.click();
        select = tbody.lastElementChild?.querySelector('select[name$="-lot"]');
      }
      if (!select) {
        signaler("Impossible d'ajouter une ligne de vente.", true);
        return;
      }

      select.value = cible.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      const ligne = select.closest("tr");
      const quantite =
        ligne?.querySelector("[data-qte]") ||
        ligne?.querySelector('input[name$="-quantite"]');
      if (quantite && (!quantite.value || quantite.value === "0")) {
        quantite.value = "1";
        quantite.dispatchEvent(new Event("input", { bubbles: true }));
      }
      quantite?.focus();
      quantite?.select?.();
      champScan.value = "";
      signaler(`Lot sélectionné : ${cible.textContent.trim()}`);
    };

    champScan.addEventListener("keydown", (evenement) => {
      if (evenement.key === "Enter") {
        evenement.preventDefault();
        traiterScan();
      }
    });

    if (champScan) {
      champScan.setAttribute("autofocus", "autofocus");
    }
  }

  const champRemise =
    document.querySelector("[data-remise]") ||
    document.querySelector('input[name="remise"]');
  if (champRemise) {
    champRemise.addEventListener("input", () => {
      const conteneur = document.querySelector("[data-formset]");
      if (conteneur) {
        conteneur.dispatchEvent(new CustomEvent("pg:recalcul"));
      }
    });
  }

  document.querySelectorAll(".btn-icon[title]").forEach((element) => {
    element.setAttribute("data-bs-toggle", "tooltip");
  });
  if (typeof bootstrap !== "undefined") {
    document.querySelectorAll(".btn-icon[title]").forEach((element) => {
      new bootstrap.Tooltip(element);
    });
  }
});