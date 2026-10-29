import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.validation import ProjectStructureInfo


# Directories to strictly ignore during scanning
IGNORED_DIRS: Set[str] = {
    ".git",
    ".github",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    "ENV",
    "site-packages",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".eggs",
    ".tox",
    ".idea",
    ".vscode",
    "node_modules",
}

# Binary and non-source extensions to ignore during source analysis
IGNORED_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".pkl",
    ".pickle",
    ".joblib",
    ".pt",
    ".pth",
    ".bin",
    ".onnx",
    ".h5",
    ".hdf5",
    ".parquet",
    ".feather",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".7z",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
    ".mp4",
    ".wav",
    ".mp3",
}

# Framework identifiers and package names
ML_FRAMEWORK_PATTERNS: Dict[str, List[str]] = {
    "PyTorch": ["torch", "torchvision", "torchaudio", "lightning", "pytorch_lightning"],
    "TensorFlow": ["tensorflow", "keras", "tensorboard"],
    "Scikit-learn": ["sklearn", "scikit-learn"],
    "XGBoost": ["xgboost"],
    "LightGBM": ["lightgbm"],
    "CatBoost": ["catboost"],
    "HuggingFace": ["transformers", "diffusers", "datasets", "accelerate", "evaluate", "timm"],
    "ONNX": ["onnx", "onnxruntime"],
    "NumPy": ["numpy"],
    "pandas": ["pandas", "polars"],
    "SciPy": ["scipy"],
    "OpenCV": ["cv2"],
    "Matplotlib/Seaborn": ["matplotlib", "seaborn"],
    "Statsmodels": ["statsmodels"],
    "NLP (spaCy/NLTK)": ["spacy", "nltk", "gensim"],
}

WEB_FRAMEWORK_PATTERNS: Dict[str, List[str]] = {
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Uvicorn": ["uvicorn"],
    "Gunicorn": ["gunicorn"],
    "Streamlit": ["streamlit"],
    "Gradio": ["gradio"],
    "Tornado": ["tornado"],
    "Bottle": ["bottle"],
}

COMMON_ENTRY_FILENAMES = [
    "main.py",
    "app.py",
    "server.py",
    "model.py",
    "predict.py",
    "inference.py",
    "serve.py",
    "api.py",
    "run.py",
    "wsgi.py",
    "handler.py",
]


class ProjectAnalyzer:
    """Scans and analyzes project structure, source files, frameworks, and entry points."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()

    def is_ignored(self, path: Path) -> bool:
        """Check if a path or any of its parents is in the ignored list."""
        try:
            rel = path.resolve().relative_to(self.project_dir)
            for part in rel.parts:
                if part in IGNORED_DIRS or part.endswith(".egg-info"):
                    return True
            return False
        except ValueError:
            return True

    def scan_structure(self) -> Tuple[ProjectStructureInfo, List[Path]]:
        """Walk the project directory and collect metadata on files, configs, and frameworks."""
        python_files: List[Path] = []
        config_files: List[str] = []
        ignored_count = 0

        has_requirements = False
        has_pyproject = False
        has_setup = False
        has_dockerfile = False

        if not self.project_dir.exists():
            return ProjectStructureInfo(), []

        for item in self.project_dir.rglob("*"):
            if self.is_ignored(item):
                ignored_count += 1
                continue

            if not item.is_file():
                continue

            rel_str = str(item.relative_to(self.project_dir)).replace("\\", "/")
            name_lower = item.name.lower()

            if item.suffix.lower() == ".py":
                python_files.append(item)
            elif name_lower == "requirements.txt":
                has_requirements = True
                config_files.append(rel_str)
            elif name_lower == "pyproject.toml":
                has_pyproject = True
                config_files.append(rel_str)
            elif name_lower in {"setup.py", "setup.cfg"}:
                has_setup = True
                config_files.append(rel_str)
            elif name_lower == "pipfile":
                config_files.append(rel_str)
            elif name_lower in {"environment.yml", "environment.yaml", "conda.yaml", "conda.yml"}:
                config_files.append(rel_str)
            elif name_lower in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
                has_dockerfile = True
                config_files.append(rel_str)

        detected_frameworks, is_ml = self.detect_frameworks(python_files)

        rel_python_files = [
            str(p.relative_to(self.project_dir)).replace("\\", "/")
            for p in python_files
        ]

        info = ProjectStructureInfo(
            total_python_files=len(python_files),
            python_files=rel_python_files,
            config_files=config_files,
            detected_frameworks=detected_frameworks,
            is_ml_project=is_ml,
            has_requirements=has_requirements,
            has_pyproject=has_pyproject,
            has_setup=has_setup,
            has_dockerfile=has_dockerfile,
            ignored_paths_count=ignored_count,
        )

        return info, python_files

    def detect_frameworks(self, python_files: List[Path]) -> Tuple[List[str], bool]:
        """Inspect imports across Python source files to identify frameworks."""
        all_imports: Set[str] = set()

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content, filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            all_imports.add(node.module.split(".")[0])
            except Exception:
                # Syntax errors or reading errors will be formally reported by CodeChecker
                continue

        frameworks: Set[str] = set()
        is_ml = False

        for fw_name, modules in ML_FRAMEWORK_PATTERNS.items():
            if any(mod in all_imports for mod in modules):
                frameworks.add(fw_name)
                # Primary ML frameworks (NumPy/Pandas alone might just be general data scripts)
                if fw_name in {
                    "PyTorch",
                    "TensorFlow",
                    "Scikit-learn",
                    "XGBoost",
                    "LightGBM",
                    "CatBoost",
                    "HuggingFace",
                    "ONNX",
                }:
                    is_ml = True

        for fw_name, modules in WEB_FRAMEWORK_PATTERNS.items():
            if any(mod in all_imports for mod in modules):
                frameworks.add(fw_name)

        # If data libraries are present alongside model/prediction terms, mark as ML
        if not is_ml and ("NumPy" in frameworks or "pandas" in frameworks):
            # Check for ML/prediction keywords in filenames
            for pf in python_files:
                name = pf.stem.lower()
                if any(k in name for k in ["train", "predict", "model", "infer", "dataset"]):
                    is_ml = True
                    break

        return sorted(list(frameworks)), is_ml

    def detect_main_entry_point(
        self,
        python_files: List[Path],
        declared_main: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """Identify the primary main application or inference entry point."""
        if declared_main:
            target = (self.project_dir / declared_main).resolve()
            if target.exists() and target.is_relative_to(self.project_dir):
                entry_type, details = self._inspect_file_for_entry(target)
                rel_str = str(target.relative_to(self.project_dir)).replace("\\", "/")
                return rel_str, entry_type, details

        # Check common root candidate filenames first
        for name in COMMON_ENTRY_FILENAMES:
            candidate = self.project_dir / name
            if candidate.exists() and candidate.is_file() and not self.is_ignored(candidate):
                entry_type, details = self._inspect_file_for_entry(candidate)
                rel_str = str(candidate.relative_to(self.project_dir)).replace("\\", "/")
                return rel_str, entry_type, details

        # Next check top-level Python files or nested ones with strong entry patterns
        scored_candidates: List[Tuple[int, Path, str, Dict[str, Any]]] = []

        for py_file in python_files:
            rel = py_file.relative_to(self.project_dir)
            score = 0

            # Favor top-level files
            if len(rel.parts) == 1:
                score += 10
            elif len(rel.parts) == 2 and rel.parts[0] in {"src", "app"}:
                score += 8

            entry_type, details = self._inspect_file_for_entry(py_file)
            if entry_type == "fastapi":
                score += 25
            elif entry_type == "flask":
                score += 20
            elif entry_type == "inference_function":
                score += 15
            elif details.get("has_main_guard"):
                score += 10

            if score > 0:
                scored_candidates.append((score, py_file, entry_type, details))

        if scored_candidates:
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            best = scored_candidates[0]
            rel_str = str(best[1].relative_to(self.project_dir)).replace("\\", "/")
            return rel_str, best[2], best[3]

        if python_files:
            # Fallback to the first python file found
            fallback = python_files[0]
            entry_type, details = self._inspect_file_for_entry(fallback)
            rel_str = str(fallback.relative_to(self.project_dir)).replace("\\", "/")
            return rel_str, entry_type, details

        return None, None, {}

    def _inspect_file_for_entry(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Parse an individual Python file's AST to detect web apps or entry functions."""
        details: Dict[str, Any] = {
            "has_main_guard": False,
            "fastapi_app_instances": [],
            "flask_app_instances": [],
            "inference_functions": [],
            "functions": [],
        }
        entry_type = "script"

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(file_path))

            for node in tree.body:
                # Check for if __name__ == '__main__':
                if isinstance(node, ast.If):
                    if self._is_name_main_comparison(node.test):
                        details["has_main_guard"] = True

                # Check for FastAPI or Flask instances: app = FastAPI()
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            if isinstance(node.value, ast.Call):
                                func = node.value.func
                                func_id = ""
                                if isinstance(func, ast.Name):
                                    func_id = func.id
                                elif isinstance(func, ast.Attribute):
                                    func_id = func.attr

                                if func_id == "FastAPI":
                                    details["fastapi_app_instances"].append(var_name)
                                    entry_type = "fastapi"
                                elif func_id == "Flask":
                                    details["flask_app_instances"].append(var_name)
                                    if entry_type != "fastapi":
                                        entry_type = "flask"

                # Check for model / prediction functions
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    details["functions"].append(node.name)
                    if node.name.lower() in {
                        "predict",
                        "inference",
                        "predict_step",
                        "run",
                        "score",
                        "handler",
                        "load_model",
                    }:
                        details["inference_functions"].append(node.name)
                        if entry_type not in {"fastapi", "flask"}:
                            entry_type = "inference_function"

            if entry_type == "script" and details["has_main_guard"]:
                entry_type = "cli_script"

        except Exception as exc:
            details["parse_error"] = str(exc)
            entry_type = "unknown"

        return entry_type, details

    @staticmethod
    def _is_name_main_comparison(test_node: ast.AST) -> bool:
        """Check if an AST node represents __name__ == '__main__'."""
        if isinstance(test_node, ast.Compare):
            left = test_node.left
            if isinstance(left, ast.Name) and left.id == "__name__":
                for comp, val in zip(test_node.ops, test_node.comparators):
                    if isinstance(comp, ast.Eq):
                        if isinstance(val, ast.Constant) and val.value == "__main__":
                            return True
        return False
