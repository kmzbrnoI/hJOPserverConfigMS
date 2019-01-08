# Konfigurační soubory hJOPserveru

Tento repozitář obsahuje konfigurační soubory layoutů [KMŽ Brno I](https://kmz-brno.cz)
pro [hJOPserver](https://github.com/kmzbrnoI/hJOPserver).

Větev `master` obsahuje soubory společné pro všechny layouty (`.gitignore`, ...),
z této větve je vhodné vycházet při vytváření nového layoutu. Každý layout má
pak svou vlastní větev.

`hJOPserver.exe` se umisťuje přímo do kořene repozitáře a odsud se spouští.

Většina stavových souborů není verzována, jediný polo-stavový soubor
je soubor `data/konfigurace.ini`, který obsahuje směsici konfiguračních
a stavových dat. Při prvním použití layoutu je doporučeno použít referenční
soubor z příslušné větve:

```
$ mv data/konfigurace.sample.ini data/konfigurace.ini
```

hJOP nadále pracuje se souborem `data/konfigurace.ini`, který je gitignorován.