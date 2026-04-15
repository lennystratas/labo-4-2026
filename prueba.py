import random

def promedio_pares(numeros):
    suma = 0
    contador = 0

    for i in (numeros):
        if i % 2 == 0:
            suma += i
            contador += 1

    if contador == 0:
        return None   
    
    return suma/ contador

numrand = []

for i in range(100):
    numrand.append(random.randint(0, 10000))

print(numrand)

print(f"El promedio de los numeros pares es {promedio_pares(numrand)}")