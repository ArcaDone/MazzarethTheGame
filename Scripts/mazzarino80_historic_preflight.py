"""Material refinement and verification in one commandlet run."""
from pathlib import Path
root=Path(__file__).resolve().parent
exec(compile((root/'mazzarino80_historic_materials.py').read_text(),'historic_materials','exec'))
exec(compile((root/'mazzarino80_historic_validate.py').read_text(),'historic_validate','exec'))
