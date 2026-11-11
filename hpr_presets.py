"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio)."""

import random
from dataclasses import dataclass

import streamlit as st

import hpr_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None
    choices: tuple | None = None   # erlaubte Werte bei Auswahlreglern


SETTING_SPECS = {
    "hand_limit_radio": SettingSpec("hlimit", int, C.DEFAULT_HAND_LIMIT, choices=C.HAND_LIMIT_OPTIONS),
    "hand_new_radio": SettingSpec("hneu", int, C.DEFAULT_HAND_NEW, choices=C.HAND_NEW_OPTIONS),
    "n_slider": SettingSpec("n", int, C.DEFAULT_N, C.N_MIN, C.N_MAX),
    "width_radio": SettingSpec("breite", int, C.DEFAULT_WIDTH, choices=C.WIDTH_OPTIONS),
    "typ_radio": SettingSpec("typ", str, C.DEFAULT_TYP, choices=C.TYP_OPTIONS),
    "k_radio": SettingSpec("k", int, C.DEFAULT_K, choices=C.K_OPTIONS),
    "limit_radio": SettingSpec("limit", int, C.DEFAULT_LIMIT, choices=C.LIMIT_OPTIONS),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "master_cost_select": SettingSpec("mkosten", int, C.DEFAULT_MASTER_COST, choices=C.MASTER_COST_OPTIONS),
    "label_cost_slider": SettingSpec("lkosten", float, C.DEFAULT_LABEL_COST, C.LABEL_COST_MIN, C.LABEL_COST_MAX),
}
PRESET_KEYS = {"hand_limit": "hand_limit_radio", "hand_new": "hand_new_radio", "n": "n_slider", "width": "width_radio", "typ": "typ_radio", "k": "k_radio", "limit": "limit_radio",
               "seed": "seed_input", "master_cost": "master_cost_select", "label_cost": "label_cost_slider"}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            if spec.choices is not None and value not in spec.choices:
                continue
            if spec.lo is not None:
                value = max(spec.lo, value)
            if spec.hi is not None:
                value = min(spec.hi, value)
            if spec.caster is float:
                value = round(round(value / C.LABEL_COST_STEP) * C.LABEL_COST_STEP, 2)   # auf das Raster des Reglers
            st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
