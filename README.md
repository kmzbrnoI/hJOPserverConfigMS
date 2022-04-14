# Konfigurační soubory hJOPserveru kolejiště Milana Sáblíka

Tento repozitář obsahuje konfigurační soubory
pro [hJOPserver](https://github.com/kmzbrnoI/hJOPserver).

`hJOPserver.exe` se umisťuje přímo do kořene repozitáře a odsud se spouští.

Většina stavových souborů není verzována, jediný polo-stavový soubor
je soubor `data/konfigurace.ini`, který obsahuje směsici konfiguračních
a stavových dat. Při prvním použití layoutu je doporučeno použít referenční
soubor z příslušné větve:

```
$ mv data/konfigurace.sample.ini data/konfigurace.ini
```

hJOP nadále pracuje se souborem `data/konfigurace.ini`, který je gitignorován.