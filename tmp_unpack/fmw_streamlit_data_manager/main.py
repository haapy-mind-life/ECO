from __future__ import annotations
import streamlit as st
from app.core.navigation import get_pages

st.set_page_config(page_title="FMW 데이터 매니저", layout="wide", page_icon="🗂️")

def main():
    st.sidebar.title("메뉴")
    pages = list(get_pages())
    labels = [p.label for p in pages]
    selected = st.sidebar.radio("", labels, index=0)
    renderer = {p.label: p.renderer for p in pages}[selected]
    renderer()

if __name__ == "__main__":
    main()
