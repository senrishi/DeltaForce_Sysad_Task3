from z3 import *


CODE = 315525
# fgets adds a null terminator at the end of the string
# so the last character is assumed as null, and it is subtracted from the CODE
# hence, z3 is used to solve for only 29 characters instead of 30

LEN = 29
temp_c = 0
temp_i = 29
total = (temp_c * temp_c) + (temp_c * (100 - temp_i)) + temp_i + (temp_c * 7) + ((temp_c | temp_i) & (temp_i + 3)) - ((temp_c * temp_c) % (temp_i + 1))
ADJUSTED_CODE = CODE - total
print(f"{total} and {ADJUSTED_CODE}")
s = Solver()
sol_var = [BitVec(f'c_{i}', 8) for i in range(LEN)]

# Constrain to printable ASCII (32-126)
for c in sol_var:
    s.add(c >= 32, c <= 126)

total_val = BitVecVal(0, 32)
for i in range(LEN):
    c = sol_var[i]
    c32 = ZeroExt(24, c)
    i8 = BitVecVal(i, 8)
    i32 = BitVecVal(i, 32)
    base = i + 1
    base_var = BitVecVal(base, 32)

    exp1 = c32 * c32
    exp2 = c32 * (100 - i)
    exp3 = i32
    4 = c32 * 7
    exp5 = (c | i8) & (i + 3)
    exp6 = ZeroExt(24, exp5)
    mod_term = URem(exp1, base_var)

    term_i = exp1 + exp2 + exp3 + exp4 + exp6 - mod_term
    total_val += term_i

s.add(total_val == ADJUSTED_CODE)

if s.check() == sat:
    model = s.model()
    sol_str = ''.join([chr(model.eval(c).as_long()) for c in sol_var])
    print(f"Found solution: {sol_str}")
else:
    print("No solution found")
