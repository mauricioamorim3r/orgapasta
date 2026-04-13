"""
NavMed — Flask Entrypoint
==========================
Serves the NavMed folder/link manager at http://localhost:5200
and launches the floating tkinter widget in a daemon thread.

Run:
    python app.py
    (or via navmed.bat for windowless start on Windows)
"""

import threading
import time
import webbrowser

from flask import Flask, render_template, Response

from api.config_api import config_bp
from api.folders import folders_bp
from api.menu_analyzer import menu_analyzer_bp

# ── App ────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
PORT = 5200

# Register blueprints
app.register_blueprint(config_bp)
app.register_blueprint(folders_bp)
app.register_blueprint(menu_analyzer_bp)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/creator")
def creator():
    return render_template("creator.html")


@app.route("/menu-analyzer")
def menu_analyzer():
    return render_template("menu_analyzer.html")


@app.route("/preview")
def preview():
    """Preview visual de todas as telas da aplicação com dados simulados."""
    return Response(_build_preview_html(), mimetype="text/html")


# ── Preview helper ────────────────────────────────────────────────────────────
def _build_preview_html():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NavMed — Preview de Telas</title>
<style>
  :root{--bg:#0f1117;--card:#1a2035;--hover:#1e2944;--border:#334155;--accent:#3b82f6;--success:#22c55e;--warning:#eab308;--danger:#ef4444;--text:#e2e8f0;--muted:#94a3b8}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#111;font-family:system-ui,sans-serif;color:var(--text);padding:24px}
  h1{color:var(--accent);font-size:20px;margin-bottom:6px}
  .subtitle{color:var(--muted);font-size:13px;margin-bottom:32px}
  .screen-label{color:var(--warning);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;padding:4px 10px;background:#78350f;border-radius:4px;display:inline-block}
  .screen{background:var(--bg);border:1px solid var(--border);border-radius:12px;margin-bottom:40px;overflow:hidden;max-width:860px}
  .screen-header{background:var(--card);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;align-items:center;gap:12px}
  .screen-body{padding:24px}
  .logo{color:var(--accent);font-weight:700;font-size:15px}
  .sep{color:var(--border)}
  .title{font-weight:600;flex:1}
  .tabs{display:flex;gap:4px;background:var(--bg);border-radius:8px;padding:3px}
  .tab{padding:5px 14px;border-radius:6px;font-size:12px;font-weight:500}
  .tab.active{background:var(--card);color:var(--text)}
  .tab.off{color:var(--muted)}
  /* upload */
  .dropzone{border:2px dashed var(--border);border-radius:10px;padding:40px 24px;text-align:center;background:var(--card);margin-bottom:18px}
  .dz-icon{font-size:40px;margin-bottom:10px}
  .dz-title{font-size:16px;font-weight:600;margin-bottom:6px}
  .dz-sub{color:var(--muted);font-size:12px;margin-bottom:14px}
  .btn{padding:8px 18px;border-radius:7px;font-size:13px;font-weight:600;border:none;cursor:default;display:inline-block}
  .btn-sec{background:var(--card);border:1px solid var(--border);color:var(--text)}
  .btn-pri{background:var(--accent);color:#fff}
  .btn-sm{padding:5px 11px;font-size:11px}
  .thumbs{display:flex;gap:10px;margin-bottom:18px}
  .thumb{width:80px;height:80px;background:var(--card);border:1px solid var(--border);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:28px;position:relative}
  .thumb-x{position:absolute;top:3px;right:3px;background:rgba(0,0,0,.6);color:#fff;width:18px;height:18px;border-radius:50%;font-size:10px;display:flex;align-items:center;justify-content:center}
  .form-row{display:flex;gap:14px;margin-bottom:14px}
  .fg{flex:1;display:flex;flex-direction:column;gap:5px}
  .fg label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
  .fg input{background:var(--card);border:1px solid var(--border);border-radius:7px;padding:7px 11px;color:var(--text);font-size:13px}
  .footer-row{display:flex;align-items:center;justify-content:space-between;margin-top:6px}
  .chk{color:var(--muted);font-size:12px}
  /* provider grid */
  .plabel{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
  .pgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:18px}
  .pcard{background:var(--card);border:2px solid var(--border);border-radius:9px;padding:12px;position:relative}
  .pcard.sel{border-color:var(--accent);background:var(--hover)}
  .picon{font-size:20px}
  .pname{font-weight:700;font-size:12px;margin-top:6px}
  .pmodel{color:var(--muted);font-size:10px;margin-top:2px}
  .badge-free{position:absolute;top:6px;right:6px;background:#14532d;color:#86efac;font-size:9px;font-weight:700;padding:2px 6px;border-radius:8px}
  /* processing */
  .proc-wrap{text-align:center;padding:60px 24px}
  .spin-ring{width:44px;height:44px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;margin:0 auto 18px;animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .proc-title{font-size:16px;font-weight:600;margin-bottom:6px}
  .proc-sub{color:var(--muted);font-size:12px}
  /* results */
  .chip{padding:4px 11px;border-radius:20px;font-size:11px;font-weight:500;display:inline-block;margin:3px}
  .chip-price{background:#1e3a5f;color:#93c5fd}
  .chip-veg{background:#14532d;color:#86efac}
  .chip-vegan{background:#064e3b;color:#6ee7b7}
  .chip-gluten{background:#7f1d1d;color:#fca5a5}
  .chip-model{background:var(--card);border:1px solid var(--border);color:var(--muted)}
  .res-actions{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
  .section{background:var(--card);border:1px solid var(--border);border-radius:9px;margin-bottom:14px;overflow:hidden}
  .sec-header{padding:13px 15px;display:flex;justify-content:space-between;align-items:center}
  .sec-title{font-weight:600;font-size:13px}
  .sec-body{padding:15px;border-top:1px solid var(--border)}
  .hgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
  .hcard{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:13px}
  .hicon{font-size:22px}
  .hlabel{color:var(--muted);font-size:10px;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}
  .hname{font-weight:600;font-size:12px;margin-top:4px}
  .hprice{color:var(--success);font-size:11px;margin-top:2px}
  .pgstat{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}
  .pstat{background:var(--bg);border-radius:8px;padding:13px;text-align:center}
  .pstat-label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.5px}
  .pstat-val{font-size:20px;font-weight:700;margin-top:4px}
  .green{color:var(--success)}.blue{color:var(--accent)}.red{color:var(--danger)}
  .cat-sec{border:1px solid var(--border);border-radius:7px;margin-bottom:8px;overflow:hidden}
  .cat-head{background:var(--bg);padding:10px 13px;display:flex;justify-content:space-between;font-weight:600;font-size:13px}
  .cat-count{background:var(--card);color:var(--muted);padding:1px 7px;border-radius:8px;font-size:10px}
  .dish{padding:11px 13px;border-top:1px solid var(--border);display:flex;gap:10px}
  .dname{font-weight:600;font-size:13px}
  .ddesc{color:var(--muted);font-size:11px;margin-top:2px}
  .dmeta{margin-top:5px;display:flex;flex-wrap:wrap;gap:3px}
  .dtag{padding:2px 7px;border-radius:4px;font-size:10px}
  .t-allerg{background:#7f1d1d;color:#fca5a5}
  .t-veg{background:#14532d;color:#86efac}
  .t-badge{background:#1e3a5f;color:#93c5fd}
  .dright{text-align:right;min-width:80px}
  .dprice{color:var(--success);font-weight:700;font-size:14px}
  .dcal{color:var(--muted);font-size:10px;margin-top:2px}
  .dstars{color:var(--warning);font-size:10px;margin-top:2px}
  .agrid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}
  .acard{background:var(--bg);border-radius:7px;padding:10px;text-align:center}
  .aicon{font-size:18px}
  .aname{color:var(--muted);font-size:10px;margin-top:3px}
  .acount{font-size:16px;font-weight:700;color:var(--warning)}
  /* history */
  .hsearch{background:var(--card);border:1px solid var(--border);border-radius:7px;padding:7px 13px;color:var(--text);font-size:13px;width:100%;margin-bottom:18px}
  .hcard2{background:var(--card);border:1px solid var(--border);border-radius:9px;padding:15px;margin-bottom:10px;display:flex;gap:12px;align-items:flex-start}
  .hcard2-icon{font-size:26px;background:var(--bg);width:46px;height:46px;border-radius:7px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .hcard2-info{flex:1}
  .hcard2-name{font-weight:700;font-size:14px}
  .hcard2-meta{color:var(--muted);font-size:11px;margin-top:3px}
  .hcard2-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
  .hcard2-actions{display:flex;flex-direction:column;gap:5px;align-items:flex-end}
  /* compare */
  .cmp-grid{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;margin-top:16px}
  .cmp-col{background:var(--card);border:1px solid var(--border);border-radius:9px;padding:15px}
  .cmp-title{font-weight:700;font-size:14px;padding-bottom:10px;border-bottom:1px solid var(--border);margin-bottom:10px}
  .cmp-stat{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:12px}
  .cmp-stat:last-child{border:none}
  .cmp-stat-label{color:var(--muted)}
  .cmp-diff{display:flex;flex-direction:column;gap:10px;align-items:center;padding-top:28px}
  .diff-card{background:var(--bg);border-radius:7px;padding:9px 13px;text-align:center;min-width:70px}
  .diff-label{color:var(--muted);font-size:9px;text-transform:uppercase}
  .diff-val{font-size:15px;font-weight:700;margin-top:2px}
  .diff-pos{color:var(--success)}.diff-neg{color:var(--danger)}.diff-n{color:var(--muted)}
</style>
</head>
<body>
<h1>NavMed — Preview de Todas as Telas</h1>
<p class="subtitle">Visualização estática com dados simulados · Servidor rodando em http://localhost:5200</p>

<!-- ══ TELA 1: Upload ══════════════════════════════════════════════════════ -->
<div class="screen-label">Tela 1 — Upload de Fotos</div>
<div class="screen">
  <div class="screen-header">
    <span class="logo">NavMed</span><span class="sep">›</span>
    <span class="title">📷 Analisador de Cardápios</span>
    <div class="tabs"><span class="tab active">Analisar</span><span class="tab off">Histórico</span></div>
  </div>
  <div class="screen-body">
    <div class="dropzone">
      <div class="dz-icon">🍽️</div>
      <div class="dz-title">Arraste as fotos do cardápio aqui</div>
      <div class="dz-sub">ou clique para selecionar · JPEG, PNG, WebP · Até 5 fotos · Máx 5 MB cada</div>
      <span class="btn btn-sec">Selecionar Fotos</span>
    </div>
    <div class="thumbs">
      <div class="thumb">📸<div class="thumb-x">✕</div></div>
      <div class="thumb">📸<div class="thumb-x">✕</div></div>
      <div class="thumb">📸<div class="thumb-x">✕</div></div>
    </div>
    <div class="form-row">
      <div class="fg"><label>Nome do Restaurante (opcional)</label><input type="text" value="La Trattoria" readonly></div>
      <div class="fg"><label>Localização / Observações (opcional)</label><input type="text" value="Rua das Flores, 42" readonly></div>
    </div>
    <div class="plabel">Modelo de IA para análise</div>
    <div class="pgrid">
      <div class="pcard"><div class="picon">🟣</div><div class="pname">Claude Sonnet</div><div class="pmodel">Anthropic · claude-sonnet-4-6</div></div>
      <div class="pcard"><div class="picon">🟢</div><div class="pname">GPT-4o</div><div class="pmodel">OpenAI · gpt-4o</div></div>
      <div class="pcard sel"><div class="picon">🔵</div><div class="pname">Gemini 2.0 Flash</div><div class="pmodel">Google · gemini-2.0-flash</div></div>
      <div class="pcard"><span class="badge-free">GRATUITO</span><div class="picon">⚡</div><div class="pname">Llama 4 Scout</div><div class="pmodel">Groq · llama-4-scout</div></div>
    </div>
    <div class="footer-row">
      <span class="chk">☑ Salvar no histórico</span>
      <span class="btn btn-pri">🔍 Analisar Cardápio</span>
    </div>
  </div>
</div>

<!-- ══ TELA 2: Processando ══════════════════════════════════════════════════ -->
<div class="screen-label">Tela 2 — Processando</div>
<div class="screen">
  <div class="screen-header">
    <span class="logo">NavMed</span><span class="sep">›</span>
    <span class="title">📷 Analisador de Cardápios</span>
    <div class="tabs"><span class="tab active">Analisar</span><span class="tab off">Histórico</span></div>
  </div>
  <div class="screen-body">
    <div class="proc-wrap">
      <div class="spin-ring"></div>
      <div style="font-size:22px;margin-bottom:8px">🍽️</div>
      <div class="proc-title">Analisando cardápio...</div>
      <div style="color:var(--muted);font-size:13px;margin-top:6px">🔵 Gemini 2.0 Flash está analisando o cardápio...</div>
      <div class="proc-sub" style="margin-top:10px">Gemini está examinando cada prato, preço e ingrediente</div>
    </div>
  </div>
</div>

<!-- ══ TELA 3: Resultados ═══════════════════════════════════════════════════ -->
<div class="screen-label">Tela 3 — Resultados da Análise</div>
<div class="screen">
  <div class="screen-header">
    <span class="logo">NavMed</span><span class="sep">›</span>
    <span class="title">📷 Analisador de Cardápios</span>
    <div class="tabs"><span class="tab active">Analisar</span><span class="tab off">Histórico</span></div>
  </div>
  <div class="screen-body">
    <div class="res-actions">
      <span class="btn btn-sec">← Nova Análise</span>
      <span class="btn btn-sec">⬇ Exportar Cardápio</span>
      <span class="btn btn-sec">📋 Ver Histórico</span>
    </div>

    <!-- Resumo -->
    <div class="section">
      <div class="sec-header"><span class="sec-title">📊 Resumo</span><span style="color:var(--muted);font-size:12px">▼</span></div>
      <div class="sec-body">
        <span class="chip chip-price">$$ Moderado ($$)</span>
        <span class="chip" style="background:var(--bg);color:var(--muted)">24 pratos</span>
        <span class="chip" style="background:var(--bg);color:var(--muted)">🏠 La Trattoria</span>
        <span class="chip chip-vegan">🌱 4 veganos</span>
        <span class="chip chip-veg">🥗 9 vegetarianos</span>
        <span class="chip chip-gluten">🌾 Glúten: 12</span>
        <span class="chip" style="background:#78350f;color:#fde68a">🥛 Lactose: 8</span>
        <span class="chip chip-model">🔵 Gemini 2.0 Flash · Google</span>
      </div>
    </div>

    <!-- Destaques -->
    <div class="section">
      <div class="sec-header"><span class="sec-title">⭐ Destaques</span><span style="color:var(--muted);font-size:12px">▼</span></div>
      <div class="sec-body">
        <div class="hgrid">
          <div class="hcard"><div class="hicon">💰</div><div class="hlabel">Melhor Custo-Benefício</div><div class="hname">Bruschetta Clássica</div><div class="hprice">R$ 22,90</div></div>
          <div class="hcard"><div class="hicon">👨‍🍳</div><div class="hlabel">Escolha do Chef</div><div class="hname">Risotto de Trufas</div><div class="hprice">R$ 68,00</div></div>
          <div class="hcard"><div class="hicon">🥗</div><div class="hlabel">Opção Saudável</div><div class="hname">Salada Mediterrânea</div><div class="hprice">R$ 34,50</div></div>
          <div class="hcard"><div class="hicon">⭐</div><div class="hlabel">Combo Popular</div><div class="hname">Bruschetta + Risotto</div></div>
        </div>
      </div>
    </div>

    <!-- Preços -->
    <div class="section">
      <div class="sec-header"><span class="sec-title">💰 Inteligência de Preços</span><span style="color:var(--muted);font-size:12px">▼</span></div>
      <div class="sec-body">
        <div class="pgstat">
          <div class="pstat"><div class="pstat-label">Mínimo</div><div class="pstat-val green">R$ 18,00</div></div>
          <div class="pstat"><div class="pstat-label">Média</div><div class="pstat-val blue">R$ 42,50</div></div>
          <div class="pstat"><div class="pstat-label">Máximo</div><div class="pstat-val red">R$ 89,00</div></div>
        </div>
      </div>
    </div>

    <!-- Cardápio completo -->
    <div class="section">
      <div class="sec-header"><span class="sec-title">🍽️ Cardápio Completo</span><span style="color:var(--muted);font-size:12px">▼</span></div>
      <div class="sec-body">
        <div class="cat-sec">
          <div class="cat-head">Entradas <span class="cat-count">4 pratos</span></div>
          <div class="dish">
            <div style="flex:1">
              <div class="dname">Bruschetta Clássica</div>
              <div class="ddesc">Pão artesanal grelhado com tomate fresco, manjericão e azeite extra virgem</div>
              <div class="dmeta">
                <span class="dtag t-allerg">🌾 Glúten</span>
                <span class="dtag t-veg">Vegetariano</span>
                <span class="dtag t-badge">💰 Melhor Valor</span>
              </div>
            </div>
            <div class="dright">
              <div class="dprice">R$ 22,90</div>
              <div class="dcal">~180 kcal</div>
              <div class="dstars">★★★★★</div>
            </div>
          </div>
          <div class="dish">
            <div style="flex:1">
              <div class="dname">Carpaccio de Salmão</div>
              <div class="ddesc">Finas fatias de salmão fresco com alcaparras, limão siciliano e rúcula</div>
              <div class="dmeta">
                <span class="dtag t-allerg">🦐 Frutos do mar</span>
              </div>
            </div>
            <div class="dright">
              <div class="dprice">R$ 38,00</div>
              <div class="dcal">~210 kcal</div>
              <div class="dstars">★★★★☆</div>
            </div>
          </div>
        </div>
        <div class="cat-sec">
          <div class="cat-head">Pratos Principais <span class="cat-count">10 pratos</span></div>
          <div class="dish">
            <div style="flex:1">
              <div class="dname">Risotto de Trufas Negras</div>
              <div class="ddesc">Arroz arbóreo cremoso com trufa negra raspada, parmesão e manteiga de ervas</div>
              <div class="dmeta">
                <span class="dtag t-allerg">🥛 Lactose</span>
                <span class="dtag t-veg">Vegetariano</span>
                <span class="dtag t-badge">👨‍🍳 Chef</span>
              </div>
            </div>
            <div class="dright">
              <div class="dprice">R$ 68,00</div>
              <div class="dcal">~580 kcal</div>
              <div class="dstars">★★★★★</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Alérgenos -->
    <div class="section">
      <div class="sec-header"><span class="sec-title">⚠️ Mapa de Alérgenos</span><span style="color:var(--muted);font-size:12px">▼</span></div>
      <div class="sec-body">
        <div class="agrid">
          <div class="acard"><div class="aicon">🌾</div><div class="aname">Glúten</div><div class="acount">12</div><div style="color:var(--muted);font-size:10px">pratos</div></div>
          <div class="acard"><div class="aicon">🥛</div><div class="aname">Lactose</div><div class="acount">8</div><div style="color:var(--muted);font-size:10px">pratos</div></div>
          <div class="acard"><div class="aicon">🥜</div><div class="aname">Nozes</div><div class="acount">3</div><div style="color:var(--muted);font-size:10px">pratos</div></div>
          <div class="acard"><div class="aicon">🦐</div><div class="aname">Frutos do mar</div><div class="acount">5</div><div style="color:var(--muted);font-size:10px">pratos</div></div>
          <div class="acard"><div class="aicon">🥚</div><div class="aname">Ovos</div><div class="acount">7</div><div style="color:var(--muted);font-size:10px">pratos</div></div>
          <div class="acard"><div class="aicon">🫘</div><div class="aname">Soja</div><div class="acount">2</div><div style="color:var(--muted);font-size:10px">pratos</div></div>
        </div>
      </div>
    </div>

    <!-- Análise Claude -->
    <div class="section">
      <div class="sec-header"><span class="sec-title">🤖 Análise Gemini</span><span style="color:var(--muted);font-size:12px">▼</span></div>
      <div class="sec-body">
        <p style="color:var(--text);line-height:1.7;font-size:13px">
          O cardápio do La Trattoria apresenta uma culinária italiana contemporânea de qualidade elevada, com destaque para ingredientes sazonais e técnicas tradicionais revisitadas.
          A faixa de preço moderada ($$) é justificada pela qualidade das matérias-primas, como as trufas negras e o salmão fresco.
          A oferta vegetariana é generosa com 9 opções, embora veganos tenham apenas 4 escolhas.
          Recomenda-se atenção a alérgenos de glúten (12 pratos) e lactose (8 pratos), presentes em grande parte do cardápio.
        </p>
      </div>
    </div>
  </div>
</div>

<!-- ══ TELA 4: Histórico ════════════════════════════════════════════════════ -->
<div class="screen-label">Tela 4 — Histórico de Análises</div>
<div class="screen">
  <div class="screen-header">
    <span class="logo">NavMed</span><span class="sep">›</span>
    <span class="title">📷 Analisador de Cardápios</span>
    <div class="tabs"><span class="tab off">Analisar</span><span class="tab active">Histórico</span></div>
  </div>
  <div class="screen-body">
    <input class="hsearch" type="text" value="🔍 Buscar restaurante..." readonly>
    <div class="hcard2">
      <div class="hcard2-icon">🍽️</div>
      <div class="hcard2-info">
        <div class="hcard2-name">La Trattoria</div>
        <div class="hcard2-meta">12/04/2026 · 3 fotos · Rua das Flores, 42</div>
        <div class="hcard2-chips">
          <span class="chip chip-price" style="padding:3px 9px;font-size:10px">$$</span>
          <span class="chip" style="background:var(--bg);color:var(--muted);padding:3px 9px;font-size:10px">24 pratos</span>
          <span class="chip chip-model" style="padding:3px 9px;font-size:10px">🔵 Gemini 2.0 Flash</span>
        </div>
      </div>
      <div class="hcard2-actions">
        <span class="btn btn-sec btn-sm">👁 Ver</span>
        <span class="btn btn-sec btn-sm">⬇ Exportar</span>
        <span class="btn btn-sec btn-sm">⚖ Comparar</span>
        <span class="btn" style="background:var(--danger);color:#fff;padding:5px 11px;font-size:11px;font-weight:600;border-radius:7px">🗑 Deletar</span>
      </div>
    </div>
    <div class="hcard2">
      <div class="hcard2-icon">🍽️</div>
      <div class="hcard2-info">
        <div class="hcard2-name">Boteco do João</div>
        <div class="hcard2-meta">10/04/2026 · 1 foto · Centro</div>
        <div class="hcard2-chips">
          <span class="chip chip-price" style="padding:3px 9px;font-size:10px">$</span>
          <span class="chip" style="background:var(--bg);color:var(--muted);padding:3px 9px;font-size:10px">19 pratos</span>
          <span class="chip chip-model" style="padding:3px 9px;font-size:10px">⚡ Llama 4 Scout</span>
        </div>
      </div>
      <div class="hcard2-actions">
        <span class="btn btn-sec btn-sm">👁 Ver</span>
        <span class="btn btn-sec btn-sm">⬇ Exportar</span>
        <span class="btn btn-sec btn-sm">⚖ Comparar</span>
        <span class="btn" style="background:var(--danger);color:#fff;padding:5px 11px;font-size:11px;font-weight:600;border-radius:7px">🗑 Deletar</span>
      </div>
    </div>
  </div>
</div>

<!-- ══ TELA 5: Comparação ═══════════════════════════════════════════════════ -->
<div class="screen-label">Tela 5 — Comparação Side-by-Side</div>
<div class="screen">
  <div class="screen-header">
    <span class="logo">NavMed</span><span class="sep">›</span>
    <span class="title">📷 Analisador de Cardápios</span>
    <div class="tabs"><span class="tab off">Analisar</span><span class="tab active">Histórico</span></div>
  </div>
  <div class="screen-body">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px">
      <h2 style="font-size:15px">Comparação de Cardápios</h2>
      <span class="btn btn-sec btn-sm">✕ Fechar</span>
    </div>
    <div class="cmp-grid">
      <div class="cmp-col">
        <div class="cmp-title">🍽️ La Trattoria</div>
        <div class="cmp-stat"><span class="cmp-stat-label">Faixa de preço</span><span>Moderado ($$)</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Preço médio</span><span class="blue">R$ 42,50</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Preço mínimo</span><span class="green">R$ 18,00</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Preço máximo</span><span class="red">R$ 89,00</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Total de pratos</span><span>24</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Veganos</span><span>4</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Vegetarianos</span><span>9</span></div>
        <div style="margin-top:10px;display:flex;gap:6px">
          <span class="btn btn-sec btn-sm">👁 Ver completo</span>
          <span class="btn btn-sec btn-sm">⬇ Exportar</span>
        </div>
      </div>
      <div class="cmp-diff">
        <div class="diff-card"><div class="diff-label">Preço médio</div><div class="diff-val diff-neg">+12,50</div></div>
        <div class="diff-card"><div class="diff-label">Pratos</div><div class="diff-val diff-pos">+5</div></div>
        <div class="diff-card"><div class="diff-label">Veganos</div><div class="diff-val diff-n">0</div></div>
        <div class="diff-card"><div class="diff-label">Vegetarianos</div><div class="diff-val diff-pos">+4</div></div>
      </div>
      <div class="cmp-col">
        <div class="cmp-title">🍽️ Boteco do João</div>
        <div class="cmp-stat"><span class="cmp-stat-label">Faixa de preço</span><span>Econômico ($)</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Preço médio</span><span class="blue">R$ 30,00</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Preço mínimo</span><span class="green">R$ 12,00</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Preço máximo</span><span class="red">R$ 55,00</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Total de pratos</span><span>19</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Veganos</span><span>4</span></div>
        <div class="cmp-stat"><span class="cmp-stat-label">Vegetarianos</span><span>5</span></div>
        <div style="margin-top:10px;display:flex;gap:6px">
          <span class="btn btn-sec btn-sm">👁 Ver completo</span>
          <span class="btn btn-sec btn-sm">⬇ Exportar</span>
        </div>
      </div>
    </div>
  </div>
</div>

<p style="color:var(--muted);font-size:12px;margin-top:16px;text-align:center">
  Acesse a aplicação real em <strong style="color:var(--accent)">http://localhost:5200/menu-analyzer</strong>
</p>
</body></html>"""


# ── Launch helpers ─────────────────────────────────────────────────────────────
def _open_browser():
    """Open the browser shortly after Flask starts."""
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")


def _start_widget():
    """Import and run the tkinter widget (runs on its own thread)."""
    try:
        import widget
        widget.run_widget()
    except Exception as exc:
        # Widget failure must not crash Flask
        print(f"[NavMed] Widget error: {exc}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  NavMed — Gerenciador de Pastas e Links")
    print(f"  http://localhost:{PORT}")
    print("=" * 50)

    # Start widget in daemon thread
    threading.Thread(target=_start_widget, daemon=True).start()

    # Open browser after short delay
    threading.Thread(target=_open_browser, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
