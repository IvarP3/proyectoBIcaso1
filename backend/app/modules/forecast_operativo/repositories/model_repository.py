from pathlib import Path
import pickle
import joblib

from app.core.config import Settings


class ModelRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve_model_path(self) -> Path:
        configured = Path(self.settings.model_file)
        if configured.exists():
            return configured

        model_dir = Path(self.settings.model_dir)
        # Buscar en orden de preferencia
        for candidate in (
            model_dir / 'transfreezer_modelo_ts.pkl',
            model_dir / 'forecast_model.pkl',
            model_dir / 'forecast_model.joblib'
        ):
            if candidate.exists():
                return candidate

        return configured

    def load_model(self, model_path: Path) -> object | None:
        if not model_path.exists():
            return None

        # Intentar pickle primero (más confiable para diccionarios complejos)
        if str(model_path).endswith('.pkl'):
            try:
                with open(model_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error cargando con pickle: {e}")
                pass
        
        # Fallback a joblib
        try:
            return joblib.load(model_path)
        except Exception as e:
            print(f"Error cargando con joblib: {e}")
            return None
