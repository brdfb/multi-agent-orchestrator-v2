"""
Ragip Aga Sub-Agent Mimarisi - Yapisal Dogrulama Testleri.

Sub-agent dosyalarinin YAML frontmatter'ini, skill dagilimini,
model secimlerini ve dosya butunlugunu test eder.
"""
import re
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).parent.parent / ".claude" / "agents"
SKILLS_DIR = Path(__file__).parent.parent / ".claude" / "skills"

# --- Yardimci fonksiyonlar ---


def parse_agent_frontmatter(filepath: Path) -> dict:
    """Agent .md dosyasindan YAML frontmatter'i parse et."""
    text = filepath.read_text(encoding="utf-8")
    match = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    assert match, f"Frontmatter bulunamadi: {filepath}"
    fm = match.group(1)

    result = {}
    # name
    m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    if m:
        result["name"] = m.group(1).strip()

    # model
    m = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
    if m:
        result["model"] = m.group(1).strip()

    # maxTurns
    m = re.search(r"^maxTurns:\s*(\d+)$", fm, re.MULTILINE)
    if m:
        result["maxTurns"] = int(m.group(1))

    # memory
    m = re.search(r"^memory:\s*(.+)$", fm, re.MULTILINE)
    if m:
        result["memory"] = m.group(1).strip()

    # skills (YAML array)
    skills = []
    in_skills = False
    for line in fm.split("\n"):
        if re.match(r"^skills:\s*\[\s*\]", line):
            # skills: []
            skills = []
            break
        if re.match(r"^skills:\s*$", line):
            in_skills = True
            continue
        if in_skills:
            m2 = re.match(r"^\s+-\s+(.+)$", line)
            if m2:
                skills.append(m2.group(1).strip())
            else:
                break
    result["skills"] = skills

    return result


# --- Agent dosyalarini yukle ---

ORCHESTRATOR_FILE = AGENTS_DIR / "ragip-aga.md"
HESAP_FILE = AGENTS_DIR / "ragip-hesap.md"
ARASTIRMA_FILE = AGENTS_DIR / "ragip-arastirma.md"
VERI_FILE = AGENTS_DIR / "ragip-veri.md"

ALL_SUBAGENT_FILES = [HESAP_FILE, ARASTIRMA_FILE, VERI_FILE]

EXPECTED_ALL_SKILLS = {
    "ragip-vade-farki",
    "ragip-ihtar",
    "ragip-analiz",
    "ragip-dis-veri",
    "ragip-gorev",
    "ragip-strateji",
    "ragip-firma",
    "ragip-import",
    "ragip-ozet",
}


# --- Test: Dosya varligi ---

class TestDosyaVarligi:
    def test_orchestrator_mevcut(self):
        assert ORCHESTRATOR_FILE.exists(), "ragip-aga.md bulunamadi"

    def test_hesap_mevcut(self):
        assert HESAP_FILE.exists(), "ragip-hesap.md bulunamadi"

    def test_arastirma_mevcut(self):
        assert ARASTIRMA_FILE.exists(), "ragip-arastirma.md bulunamadi"

    def test_veri_mevcut(self):
        assert VERI_FILE.exists(), "ragip-veri.md bulunamadi"


# --- Test: Orchestrator yapilandirmasi ---

class TestOrchestrator:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.fm = parse_agent_frontmatter(ORCHESTRATOR_FILE)

    def test_isim(self):
        assert self.fm["name"] == "ragip-aga"

    def test_model_sonnet(self):
        assert self.fm["model"] == "sonnet"

    def test_skills_bos(self):
        """Orchestrator'de skill olmamali — hepsi sub-agent'larda"""
        assert self.fm["skills"] == [], (
            f"Orchestrator'de skill var: {self.fm['skills']}"
        )

    def test_max_turns(self):
        assert self.fm["maxTurns"] >= 10, "maxTurns multi-step icin yeterli olmali"

    def test_memory_project(self):
        assert self.fm.get("memory") == "project"

    def test_dispatch_tablosu(self):
        """System prompt'ta 3 sub-agent referansi olmali"""
        text = ORCHESTRATOR_FILE.read_text(encoding="utf-8")
        assert "ragip-hesap" in text, "ragip-hesap dispatch referansi eksik"
        assert "ragip-arastirma" in text, "ragip-arastirma dispatch referansi eksik"
        assert "ragip-veri" in text, "ragip-veri dispatch referansi eksik"

    def test_paralel_kurallari(self):
        """Paralel calistirma kurallari olmali"""
        text = ORCHESTRATOR_FILE.read_text(encoding="utf-8")
        assert "PARALEL" in text.upper(), "Paralel calistirma kurallari eksik"


# --- Test: Sub-agent yapilandirmasi ---

class TestSubAgentHesap:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.fm = parse_agent_frontmatter(HESAP_FILE)

    def test_isim(self):
        assert self.fm["name"] == "ragip-hesap"

    def test_model_haiku(self):
        """Hesap motoru icin haiku yeterli (deterministik hesaplama)"""
        assert self.fm["model"] == "haiku"

    def test_skills(self):
        assert self.fm["skills"] == ["ragip-vade-farki"]

    def test_max_turns_kisa(self):
        assert self.fm["maxTurns"] <= 5, "Hesap motoru 3-5 turn yeterli"


class TestSubAgentArastirma:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.fm = parse_agent_frontmatter(ARASTIRMA_FILE)

    def test_isim(self):
        assert self.fm["name"] == "ragip-arastirma"

    def test_model_sonnet(self):
        """Arastirma/analiz icin sonnet gerekli (derin dusunme)"""
        assert self.fm["model"] == "sonnet"

    def test_skills(self):
        expected = {"ragip-analiz", "ragip-dis-veri", "ragip-strateji", "ragip-ihtar"}
        assert set(self.fm["skills"]) == expected

    def test_max_turns(self):
        assert self.fm["maxTurns"] >= 5, "Arastirma icin 5+ turn gerekli"

    def test_memory(self):
        assert self.fm.get("memory") == "project"

    def test_yasal_referanslar(self):
        """System prompt'ta yasal referans cercevesi olmali"""
        text = ARASTIRMA_FILE.read_text(encoding="utf-8")
        assert "TBK" in text, "TBK referansi eksik"
        assert "TTK" in text, "TTK referansi eksik"
        assert "IIK" in text, "IIK referansi eksik"


class TestSubAgentVeri:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.fm = parse_agent_frontmatter(VERI_FILE)

    def test_isim(self):
        assert self.fm["name"] == "ragip-veri"

    def test_model_haiku(self):
        """CRUD islemleri icin haiku yeterli"""
        assert self.fm["model"] == "haiku"

    def test_skills(self):
        expected = {"ragip-firma", "ragip-gorev", "ragip-import", "ragip-ozet"}
        assert set(self.fm["skills"]) == expected

    def test_max_turns_kisa(self):
        assert self.fm["maxTurns"] <= 5, "CRUD islemleri 3-5 turn yeterli"


# --- Test: Skill dagilimi butunlugu ---

class TestSkillDagilimi:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.hesap = parse_agent_frontmatter(HESAP_FILE)
        self.arastirma = parse_agent_frontmatter(ARASTIRMA_FILE)
        self.veri = parse_agent_frontmatter(VERI_FILE)
        self.all_subagents = [self.hesap, self.arastirma, self.veri]

    def test_tum_skilller_atanmis(self):
        """9 skill'in tamami sub-agent'lara atanmis olmali"""
        assigned = set()
        for agent in self.all_subagents:
            assigned.update(agent["skills"])
        assert assigned == EXPECTED_ALL_SKILLS, (
            f"Eksik skill'ler: {EXPECTED_ALL_SKILLS - assigned}"
        )

    def test_skill_cakismasi_yok(self):
        """Hicbir skill birden fazla agent'ta olmamali"""
        all_skills = []
        for agent in self.all_subagents:
            all_skills.extend(agent["skills"])
        assert len(all_skills) == len(set(all_skills)), (
            f"Cakisan skill var: {[s for s in all_skills if all_skills.count(s) > 1]}"
        )

    def test_skill_dosyalari_mevcut(self):
        """Her atanmis skill'in SKILL.md dosyasi olmali"""
        for agent in self.all_subagents:
            for skill in agent["skills"]:
                skill_file = SKILLS_DIR / skill / "SKILL.md"
                assert skill_file.exists(), (
                    f"Skill dosyasi bulunamadi: {skill}/SKILL.md "
                    f"(agent: {agent['name']})"
                )

    def test_orchestrator_skill_yok(self):
        """Orchestrator'de dogrudan skill olmamali"""
        orch = parse_agent_frontmatter(ORCHESTRATOR_FILE)
        assert orch["skills"] == [], "Orchestrator'de skill olmamali"

    def test_toplam_skill_sayisi(self):
        """Tam 9 skill olmali"""
        total = sum(len(a["skills"]) for a in self.all_subagents)
        assert total == 9, f"Beklenen 9 skill, bulunan {total}"


# --- Test: Skill disable-model-invocation tutarliligi ---

class TestSkillModelInvocation:
    """disable-model-invocation: true olan skill'ler veri/template skill'leri olmali"""

    EXPECTED_DISABLED = {"ragip-firma", "ragip-gorev", "ragip-ihtar", "ragip-ozet", "ragip-import"}

    def _has_disable_flag(self, skill_name: str) -> bool:
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        return "disable-model-invocation: true" in text

    def test_beklenen_disabled_skilller(self):
        """Prosedural skill'ler disable-model-invocation: true olmali"""
        for skill in self.EXPECTED_DISABLED:
            assert self._has_disable_flag(skill), (
                f"{skill} icin disable-model-invocation: true eksik"
            )

    def test_llm_gerektiren_skilller(self):
        """LLM gerektiren skill'lerde disable-model-invocation olmamali"""
        llm_skills = EXPECTED_ALL_SKILLS - self.EXPECTED_DISABLED
        for skill in llm_skills:
            assert not self._has_disable_flag(skill), (
                f"{skill} LLM gerektiriyor ama disable-model-invocation: true var"
            )


# --- Test: Cikti yonetimi ---

class TestCiktiYonetimi:
    """Alt-ajanlarin cikti kaydetme talimatlari dogru yapilandirilmis olmali"""

    def test_orchestrator_cikti_yonetimi_bolumu(self):
        """ragip-aga.md'de CIKTI YONETIMI bolumu olmali"""
        text = ORCHESTRATOR_FILE.read_text(encoding="utf-8")
        assert "CIKTI YONETIMI" in text, (
            "Orchestrator'de CIKTI YONETIMI bolumu eksik"
        )

    def test_orchestrator_ciktilar_dizin_referansi(self):
        """Orchestrator ciktilar/ dizinine referans vermeli"""
        text = ORCHESTRATOR_FILE.read_text(encoding="utf-8")
        assert "ciktilar/" in text, (
            "Orchestrator'de ciktilar/ dizin referansi eksik"
        )

    def test_arastirma_cikti_kaydetme(self):
        """ragip-arastirma cikti kaydetme talimati icermeli"""
        text = ARASTIRMA_FILE.read_text(encoding="utf-8")
        assert "CIKTI KAYDETME" in text, (
            "ragip-arastirma'da CIKTI KAYDETME bolumu eksik"
        )
        assert "ciktilar/" in text, (
            "ragip-arastirma'da ciktilar/ dizin referansi eksik"
        )

    def test_hesap_cikti_kaydetme(self):
        """ragip-hesap cikti kaydetme talimati icermeli"""
        text = HESAP_FILE.read_text(encoding="utf-8")
        assert "CIKTI KAYDETME" in text, (
            "ragip-hesap'ta CIKTI KAYDETME bolumu eksik"
        )
        assert "ciktilar/" in text, (
            "ragip-hesap'ta ciktilar/ dizin referansi eksik"
        )

    def test_veri_cikti_kaydetme(self):
        """ragip-veri cikti kaydetme talimati icermeli"""
        text = VERI_FILE.read_text(encoding="utf-8")
        assert "CIKTI KAYDETME" in text, (
            "ragip-veri'de CIKTI KAYDETME bolumu eksik"
        )

    def test_tum_subagentlar_cikti_dizini_ayni(self):
        """Tum sub-agent'lar ayni cikti dizinine yazamali"""
        beklenen = "ciktilar/"
        for f in ALL_SUBAGENT_FILES:
            text = f.read_text(encoding="utf-8")
            assert beklenen in text, (
                f"{f.name} icinde '{beklenen}' referansi eksik"
            )
