import os
import shutil
import string
from pathlib import Path


def titulo() -> None:
    print()
    print("=" * 60)
    print("              FILE ORGANIZER")
    print("=" * 60)
    print()


def perguntar_busca() -> list[str]:
    print("O que voce quer procurar?")
    print("Exemplo: XYZ")
    print("Voce tambem pode usar varios termos: XYZ, contrato, proposta")
    print()

    while True:
        texto: str = input("> ").strip()

        if texto:
            return [
                termo.strip().lower()
                for termo in texto.split(",")
                if termo.strip()
            ]

        print("Informe pelo menos um termo.")


def perguntar_tipo() -> str:
    print()
    print("Tipo de busca:")
    print()
    print("1 - Nome contem")
    print("2 - Nome comeca com")
    print("3 - Nome exato")
    print("4 - Extensao")
    print()

    while True:
        opcao: str = input("> ").strip()

        if opcao in ["1", "2", "3", "4"]:
            return opcao

        print("Opcao invalida.")


def perguntar_local():
    print()
    print("Onde procurar?")
    print()
    print("1 - Diretorio especifico")
    print("2 - Computador inteiro")
    print()

    while True:
        opcao: str = input("> ").strip()

        if opcao in ["1", "2"]:
            break

        print("Opcao invalida.")

    if opcao == "1":

        while True:
            diretorio: str = input(
                "\nDigite o caminho do diretorio:\n> "
            ).strip().strip('"')

            caminho = Path(diretorio)

            if caminho.is_dir():
                return [caminho]

            print("Diretorio nao encontrado.")

    # Windows
    if os.name == "nt":

        unidades = []

        for letra in string.ascii_uppercase:

            unidade = Path(f"{letra}:\\")

            if unidade.exists():
                unidades.append(unidade)

        return unidades

    # Linux / Mac
    return [Path("/")]


def arquivo_corresponde(arquivo, termos, tipo) -> bool:

    nome = arquivo.name.lower()

    # Nome contem
    if tipo == "1":

        for termo in termos:

            if termo in nome:
                return True

        return False

    # Comeca com
    if tipo == "2":

        for termo in termos:

            if nome.startswith(termo):
                return True

        return False

    # Nome exato
    if tipo == "3":

        for termo in termos:

            if nome == termo:
                return True

        return False

    # Extensao
    if tipo == "4":

        for termo in termos:

            extensao = termo

            if not extensao.startswith("."):
                extensao = "." + extensao

            if arquivo.suffix.lower() == extensao:
                return True

        return False

    return False


def procurar(raizes, termos, tipo):

    encontrados = []

    print()
    print("=" * 60)
    print("BUSCANDO ARQUIVOS...")
    print("=" * 60)
    print()

    for raiz in raizes:

        print(f"Analisando: {raiz}")

        try:

            for pasta_atual, pastas, arquivos in os.walk(
                raiz,
                topdown=True
            ):

                # Remove pastas do Windows que nao precisamos analisar
                pastas[:] = [
                    pasta
                    for pasta in pastas
                    if pasta not in [
                        "$Recycle.Bin",
                        "System Volume Information"
                    ]
                ]

                for nome_arquivo in arquivos:

                    arquivo = Path(pasta_atual) / nome_arquivo

                    try:

                        if arquivo_corresponde(
                            arquivo,
                            termos,
                            tipo
                        ):
                            encontrados.append(arquivo)

                    except (PermissionError, OSError):
                        pass

        except (PermissionError, OSError):

            print(
                f"Sem permissao para acessar: {raiz}"
            )

    return encontrados


def mostrar_arquivos(arquivos) -> None:

    print()
    print("=" * 60)
    print(f"ARQUIVOS ENCONTRADOS: {len(arquivos)}")
    print("=" * 60)

    if not arquivos:
        print()
        print("Nenhum arquivo encontrado.")
        return

    for numero, arquivo in enumerate(
        arquivos,
        start=1
    ):

        print()
        print(f"{numero}. {arquivo.name}")
        print(f"   {arquivo}")


def caminho_disponivel(caminho):

    if not caminho.exists():
        return caminho

    contador = 1

    while True:

        novo_nome: str = (
            f"{caminho.stem} "
            f"({contador})"
            f"{caminho.suffix}"
        )

        novo_caminho = (
            caminho.parent / novo_nome
        )

        if not novo_caminho.exists():
            return novo_caminho

        contador += 1


def mover(arquivos, nome_destino) -> None:

    movidos = 0
    erros = 0

    print()
    print("=" * 60)
    print("MOVENDO ARQUIVOS...")
    print("=" * 60)

    for arquivo in arquivos:

        try:

            # Cria a pasta destino no mesmo local
            # onde o arquivo foi encontrado.
            pasta_destino = (
                arquivo.parent / nome_destino
            )

            pasta_destino.mkdir(
                parents=True,
                exist_ok=True
            )

            destino = (
                pasta_destino / arquivo.name
            )

            destino = caminho_disponivel(
                destino
            )

            shutil.move(
                str(arquivo),
                str(destino)
            )

            print(f"[OK] {arquivo.name}")
            print(f"     -> {destino}")
            print()

            movidos += 1

        except PermissionError:

            print(
                f"[ERRO] Sem permissao: {arquivo}"
            )

            erros += 1

        except OSError as erro:
            print(
                f"[ERRO] {arquivo}"
            )

            print(
                f"       {erro}"
            )

            erros += 1

    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)

    print(f"Encontrados: {len(arquivos)}")
    print(f"Movidos:     {movidos}")
    print(f"Erros:       {erros}")


def main() -> None:

    titulo()

    termos: list[str] = perguntar_busca()

    tipo: str = perguntar_tipo()

    raizes = perguntar_local()

    print()

    while True:

        nome_destino: str = input(
            "Nome da pasta de destino:\n> "
        ).strip()

        if not nome_destino:
            print("Informe o nome da pasta.")
            continue

        caracteres_invalidos = '<>:"/\\|?*'

        if any(
            caractere in nome_destino
            for caractere in caracteres_invalidos
        ):

            print(
                "O nome possui caracteres invalidos."
            )

            continue

        break

    print()
    print("=" * 60)
    print("CONFIGURACAO")
    print("=" * 60)

    print(
        "Termos:",
        ", ".join(termos)
    )

    tipos: dict[str, str] = {
        "1": "Nome contem",
        "2": "Nome comeca com",
        "3": "Nome exato",
        "4": "Extensao"
    }

    print(
        "Tipo:",
        tipos[tipo]
    )

    print(
        "Destino:",
        nome_destino
    )

    print()
    print("Locais de busca:")

    for raiz in raizes:
        print(f"  {raiz}")

    print()

    input(
        "Pressione ENTER para iniciar a busca..."
    )

    arquivos = procurar(
        raizes,
        termos,
        tipo
    )

    mostrar_arquivos(arquivos)

    if not arquivos:

        input(
            "\nPressione ENTER para sair..."
        )

        return

    print()

    resposta: str = input(
        "Deseja mover esses arquivos? [s/N]: "
    ).strip().lower()

    if resposta not in ["s", "sim"]:

        print()
        print("Operacao cancelada.")

        input(
            "\nPressione ENTER para sair..."
        )

        return

    mover(
        arquivos,
        nome_destino
    )

    print()
    print("Organizacao concluida!")

    input(
        "\nPressione ENTER para sair..."
    )


if __name__ == "__main__":
    main()
