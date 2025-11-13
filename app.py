import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
import os
from config import Config
from extensions import db, migrate, init_mongo
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from auth import init_login_manager, get_user_context


def _is_api_request():
    try:
        path = request.path or ''
        accept = (request.headers.get('Accept') or '').lower()
        return path.startswith('/api/') or ('application/json' in accept)
    except Exception:
        return False

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='assets', static_url_path='/static')
    app.config.from_object(config_class)
    try:
        app.config['TESTING'] = getattr(config_class, 'TESTING', app.config.get('TESTING', False))
    except Exception:
        pass

    # Inicializar extensões
    # SQLAlchemy é mantido apenas para compatibilidade, não criar tabelas
    db.init_app(app)
    migrate.init_app(app, db)

    # MongoDB (persistência oficial)
    try:
        init_mongo(app)
        app.config['MONGO_AVAILABLE'] = True
    except Exception as e:
        # Permitir inicialização do app para preview local mesmo sem Mongo.
        # Rotas que dependem de Mongo devem lidar com a indisponibilidade.
        app.config['MONGO_AVAILABLE'] = False
        print(f"[WARN] MongoDB indisponível: {e}. Inicializando app sem Mongo para preview.")

    # Login manager
    init_login_manager(app)

    # Contexto global para templates (usuário, widgets, flags de acesso)
    @app.context_processor
    def inject_user_context_global():
        return get_user_context()

    # Registrar blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    try:
        app.config['START_TIME'] = app.config.get('START_TIME') or __import__('time').time()
    except Exception:
        pass

    class _ReqIdFilter(logging.Filter):
        def filter(self, record):
            try:
                from flask import g
                rid = getattr(g, 'request_id', None) or '-'
                record.request_id = rid
            except Exception:
                record.request_id = '-'
            return True

    try:
        log_level_name = str(__import__('os').environ.get('LOG_LEVEL', 'INFO')).upper()
    except Exception:
        log_level_name = 'INFO'
    app.logger.setLevel(getattr(logging, log_level_name, logging.INFO))
    try:
        log_file = str(__import__('os').environ.get('LOG_FILE') or '')
        if log_file:
            handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
            fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s [req:%(request_id)s] %(message)s')
            handler.setFormatter(fmt)
            handler.addFilter(_ReqIdFilter())
            app.logger.addHandler(handler)
    except Exception:
        pass

    @app.before_request
    def _req_id_provisioning():
        try:
            import uuid
            rid = request.headers.get('X-Request-ID') or str(uuid.uuid4())
            from flask import g
            g.request_id = rid
        except Exception:
            pass

    @app.after_request
    def _set_security_headers(resp):
        try:
            resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
            resp.headers.setdefault('X-Frame-Options', 'DENY')
            resp.headers.setdefault('Referrer-Policy', 'no-referrer')
            resp.headers.setdefault(
                'Content-Security-Policy',
                "default-src 'self' https:; script-src 'self' https: 'unsafe-inline'; style-src 'self' https: 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https: data:"
            )
            try:
                from flask import g
                rid = getattr(g, 'request_id', None)
                if rid:
                    resp.headers.setdefault('X-Request-ID', rid)
            except Exception:
                pass
        except Exception:
            pass
        return resp

    @app.errorhandler(404)
    def _handle_404(e):
        if _is_api_request():
            return jsonify({'error': 'Not Found', 'code': 404}), 404
        return ("<h1>404</h1><p>Página não encontrada.</p>", 404)

    @app.errorhandler(500)
    def _handle_500(e):
        if _is_api_request():
            return jsonify({'error': 'Internal Server Error', 'code': 500}), 500
        return ("<h1>500</h1><p>Erro interno do servidor.</p>", 500)

    return app

# Expor o app para gunicorn
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(debug=True, host=host, port=port)
