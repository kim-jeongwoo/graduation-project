"""
서버 환경 설정 확인 스크립트
egg_prediction 프로젝트 - SVD 기반 화자 독립 모델 학습 환경
"""
import sys
import os

def check_package(name):
    try:
        mod = __import__(name)
        ver = getattr(mod, '__version__', '✓')
        return True, ver
    except ImportError:
        return False, None

print("=" * 60)
print("           서버 환경 세팅 결과")
print("=" * 60)

# ── 시스템 ──
print("\n📌 시스템:")
print(f"   OS: Ubuntu {os.popen('lsb_release -rs 2>/dev/null').read().strip() or 'N/A'}")
print(f"   User: {os.environ.get('USER', 'N/A')}")
print(f"   Home: {os.path.expanduser('~')}")

# ── GPU ──
print("\n📌 GPU:")
import torch
print(f"   CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   CUDA version: {torch.version.cuda}")
    print(f"   GPU 이름: {torch.cuda.get_device_name(0)}")
    mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"   GPU 메모리: {mem_gb:.1f} GB")
    # GPU 연산 테스트
    try:
        x = torch.randn(2000, 2000, device='cuda')
        y = torch.matmul(x, x)
        del x, y
        torch.cuda.empty_cache()
        print(f"   GPU 연산 테스트: ✅ 정상")
    except Exception as e:
        print(f"   GPU 연산 테스트: ❌ {e}")
else:
    print("   ⚠️  GPU 확인 필요!")

# ── Python 환경 ──
print("\n📌 Python 환경:")
print(f"   Python: {sys.version.split()[0]}")
print(f"   PyTorch: {torch.__version__}")
print(f"   CUDA 지원: {'✅' if torch.cuda.is_available() else '❌'}")

# ── 패키지 설치 ──
print("\n📌 패키지 설치:")
packages = ['numpy', 'scipy', 'librosa', 'soundfile', 'pandas',
            'matplotlib', 'tqdm', 'sklearn', 'yaml']
pkg_display = {'sklearn': 'scikit-learn', 'yaml': 'pyyaml'}
for pkg in packages:
    ok, ver = check_package(pkg)
    display = pkg_display.get(pkg, pkg)
    if ok:
        print(f"   {display}: ✅ ({ver})")
    else:
        print(f"   {display}: ❌ 설치 필요")

# ── 프로젝트 폴더 ──
print("\n📌 프로젝트 폴더:")
home = os.path.expanduser("~")
project_path = f"{home}/projects/egg_prediction"
subdirs = ['data/raw', 'data/processed', 'model', 'utils',
           'results', 'checkpoints', 'configs']
print(f"   {project_path}: {'✅' if os.path.exists(project_path) else '❌'}")
for sd in subdirs:
    full = os.path.join(project_path, sd)
    print(f"     └─ {sd}: {'✅' if os.path.exists(full) else '❌'}")

# ── 데이터 경로 ──
print("\n📌 데이터 경로:")
data_paths = {
    "SVD_healthy": f"{project_path}/data/raw/SVD_healthy",
    "PTDB-TUG": f"{project_path}/data/raw/PTDB-TUG",
}
for name, p in data_paths.items():
    if os.path.exists(p):
        count = len(os.listdir(p))
        print(f"   {name}: ✅ ({count}개 항목)")
    else:
        print(f"   {name}: ❌ (전송 필요)")

# ── Config 파일 ──
print("\n📌 Config 파일:")
config_path = f"{project_path}/configs/config.yaml"
print(f"   config.yaml: {'✅' if os.path.exists(config_path) else '❌'}")

# ── 다음 단계 ──
print("\n" + "=" * 60)
print("📋 다음 단계:")

has_data = all(os.path.exists(p) for p in data_paths.values())
if not has_data:
    print("   1. Mac에서 데이터 전송 필요")
    print("      Mac 터미널에서:")
    print(f"      scp -r ~/Desktop/졸업작품/workspace/data/raw/SVD_healthy \\")
    print(f"        dmlserver@<서버IP>:{project_path}/data/raw/")
    print(f"      scp -r ~/Desktop/졸업작품/workspace/data/raw/PTDB-TUG \\")
    print(f"        dmlserver@<서버IP>:{project_path}/data/raw/")
    print("   2. 전송 후 학습 시작 가능")
else:
    print("   ✅ 데이터 준비 완료! 학습 시작 가능")

print("=" * 60)
