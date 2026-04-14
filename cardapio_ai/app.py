"""Standalone Flask app for menu photo analysis."""

from flask import Flask, jsonify, render_template

from api.routes import menu_bp


PORT = 5300


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(menu_bp)

    @app.route('/')
    def index() -> str:
        return render_template('index.html')

    @app.route('/health')
    def health() -> tuple[dict, int]:
        return jsonify({'ok': True, 'service': 'fotocardapio-ai'}), 200

    return app


app = create_app()


if __name__ == '__main__':
    print('=' * 50)
    print('  FotoCardapio AI - Analise de Cardapios por Foto')
    print(f'  http://localhost:{PORT}')
    print('=' * 50)
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)