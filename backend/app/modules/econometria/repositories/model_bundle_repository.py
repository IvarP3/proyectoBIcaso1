from pathlib import Path
import pickle
import joblib

from app.core.config import Settings


class ModelBundleRepository:
	def __init__(self, settings: Settings) -> None:
		self.settings = settings

	def resolve_model_path(self) -> Path:
		configured = Path(self.settings.econometria_model_file)
		if configured.exists():
			return configured

		model_dir = Path(self.settings.econometria_model_dir)
		for candidate in (
			model_dir / 'transfreezer_modelo_econometrico_v1.pkl',
			model_dir / 'transfreezer_modelo_econometrico_v1.plk',
			Path('app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_econometrico_v1.pkl'),
			Path('app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_econometrico_v1.plk'),
			Path('app/modules/forecast_operativo/artifacts/models/transfreezer_modelo_ts.pkl'),
		):
			if candidate.exists():
				return candidate

		return configured

	def load_bundle(self, model_path: Path) -> object | None:
		if not model_path.exists():
			return None

		if str(model_path).endswith('.pkl') or str(model_path).endswith('.plk'):
			try:
				with open(model_path, 'rb') as file_handle:
					return pickle.load(file_handle)
			except Exception:
				pass

		try:
			return joblib.load(model_path)
		except Exception:
			return None
