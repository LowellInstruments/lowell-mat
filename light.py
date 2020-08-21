DEFAULT_PDA = 100.0
DEFAULT_PDB = -100/4096


class Light:
    def __init__(self, calibration):
        self.pda = calibration.coefficients.get("PDA", DEFAULT_PDA)
        self.pdb = calibration.coefficients.get("PDB", DEFAULT_PDB)

    def convert(self, raw_light):
        is_bad_val = raw_light > 4096
        light_val = raw_light * self.pdb + self.pda
        light_val[is_bad_val] = -1
        return light_val
