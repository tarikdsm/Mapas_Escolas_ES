# Estrutura de Testes

## Pastas

- `tests/scripts/`: codigo dos testes e runner local
- `tests/docs/`: notas operacionais da suite
- `tests/logs/`: logs das execucoes locais

## Runner principal

```bash
python3 tests/scripts/run_tests.py
```

O runner descobre automaticamente os arquivos `test_*.py` e grava o ultimo resultado em `tests/logs/latest-test-run.log`.

## Escopo atual

- API do backend
- CRUD e consistencia dos exports do frontend
- seguranca basica de rotas estaticas e tratamento de erro
- disponibilidade das paginas principais e assets criticos
