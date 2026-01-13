# Issue #562: Floating-point zero comparison в feature_correlation

## Что изменено
- Заменено прямое сравнение `np.std(...) == 0` на `np.isclose(np.std(...), 0)`
- Это корректно обрабатывает floating-point погрешности (e.g., 1e-16 вместо 0)

## Затронутые файлы
- `src/services/feature_correlation.py:226`

## Test
```bash
python3 -c "
import numpy as np

# Симулируем проверку как в feature_correlation.py:226
# До исправления: np.std(...) == 0
# После исправления: np.isclose(np.std(...), 0)

# Test 1: Floating-point near-zero должен детектироваться как zero
values_with_noise = np.array([1.0 + i*1e-16 for i in range(50)])
std_value = np.std(values_with_noise)
print(f'std with floating-point noise: {std_value}')

# Старый код: == 0 не сработает
old_check = (std_value == 0)
# Новый код: isclose сработает
new_check = np.isclose(std_value, 0)

assert not old_check, f'Old check should NOT detect near-zero, but got {old_check}'
assert new_check, f'New check should detect near-zero, but got {new_check}'

# Test 2: Настоящий zero детектируется обоими способами
exact_zero = np.std([1.0] * 50)
assert exact_zero == 0
assert np.isclose(exact_zero, 0)

# Test 3: Нормальная дисперсия НЕ должна детектироваться как zero
normal_values = np.array([float(i) for i in range(50)])
normal_std = np.std(normal_values)
assert not np.isclose(normal_std, 0), f'Normal std {normal_std} should not be near zero'

print('OK: np.isclose correctly handles floating-point precision')
"
```
