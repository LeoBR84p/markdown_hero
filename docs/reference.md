# markdown_hero — Referência técnica

Esta documentação descreve cada função pública, seus parâmetros, comportamento
e exemplos de uso. A versão atual é **0.1.0**, Python ≥ 3.10, dialeto-alvo
**GFM** (GitHub Flavored Markdown).

## Índice

1. [`strip`](#strip) — texto plano normalizado
2. [`extract_chunks`](#extract_chunks) — chunking estrutural
3. [`word_format`](#word_format) — exportação para .docx
4. [`markdown_append`](#markdown_append) — concatenação
5. [`markdown_break`](#markdown_break) — divisão por delimitadores
6. [`markdown_merge`](#markdown_merge) — append “inteligente”
7. [Funções de extração](#extracao) — frontmatter, links, imagens, tabelas, código, headings, TOC
8. [Funções de transformação](#transformacao) — normalize, slugify, shift_headings, strip_*
9. [Lint e métricas](#lint) — `lint`, `word_count`, `reading_time`
10. [CLI](#cli)
11. [Modelos de dados](#modelos)
12. [Decisões de design](#design)
13. [Limites e segurança](#limites)

---

<a id="strip"></a>

## 1. `strip(text, *, keep_numbers=True, keep_math=False, keep_latex_text=False) -> str`

Reduz Markdown a um único texto: minúsculas, sem acentos (NFKD), sem
pontuação, sem marcação. Múltiplos espaços e quebras viram um espaço único.

### Parâmetros

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `text` | `str` | — | Conteúdo Markdown a normalizar. |
| `keep_numbers` | `bool` | `True` | Preserva dígitos. |
| `keep_math` | `bool` | `False` | Preserva sinais matemáticos: `=`, `<`, `>`, `≤`, `≥`, `≠`, `±`, `×`, `÷`, `%`, `°`, `+`, `/`. |
| `keep_latex_text` | `bool` | `False` | Em vez de remover fórmulas `$...$`/`$$...$$`, desembrulha o conteúdo como texto. |

### Comportamento

- Blocos de código, inline code, HTML inline, fórmulas LaTeX, links e imagens
  são processados antes da normalização.
- Em links e imagens, o texto/alt é preservado e a URL descartada.
- Símbolos matemáticos (`=`) **deletam-se sem deixar espaço**, então `p=2` vira `p2`.
- Pontuação e símbolos genéricos (`.,;:!?()[]{}`) viram espaço.
- Após NFKD, caracteres não-ASCII residuais são removidos.

### Exemplo

```python
from markdown_hero import strip

md = """**Compromisso entre média e máximo.**
p=1 (média aritmética ponderada) ignora concentração.
p=2 captura ambos."""

strip(md)
# 'compromisso entre media e maximo p1 media aritmetica ponderada
#  ignora concentracao p2 captura ambos'

strip(md, keep_math=True)
# '... p=1 ... p=2 ...'

strip("A formula $x = y + 1$.", keep_latex_text=True)
# 'a formula x y 1'
```

---

<a id="extract_chunks"></a>

## 2. `extract_chunks(md, *, strategy=None, purpose="generic", max_tokens=0, overlap=0, tokenizer=None, source=None, min_tokens=0) -> list[Chunk]`

Divide um documento em pedaços com metadados estruturais úteis para RAG,
fine-tuning, sumarização etc.

### Estratégias

| Estratégia | Comportamento |
|---|---|
| `structural` | Quebra por hierarquia de headings; cada seção vira um chunk. |
| `semantic` | Agrupa parágrafos até `max_tokens`. |
| `fixed` | Corte rígido por tokens. |
| `hybrid` | Estrutural + sub-split por tokens dentro de seções grandes. |

### Defaults por `purpose`

| `purpose` | `strategy` | `max_tokens` | `overlap` |
|---|---|---|---|
| `rag` | `hybrid` | 512 | 64 |
| `finetune` | `structural` | 1024 | 0 |
| `summary` | `structural` | 2048 | 0 |
| `generic` | `structural` | 512 | 0 |

### Parâmetros

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `md` | `str` | Markdown completo. |
| `strategy` | `str \| None` | Sobrescreve a estratégia derivada de `purpose`. |
| `purpose` | `"rag"\|"finetune"\|"summary"\|"generic"` | Define defaults sensatos. |
| `max_tokens` | `int` | Override do limite de tokens; `0` usa default do purpose. |
| `overlap` | `int` | Tokens de sobreposição entre chunks consecutivos da mesma seção. |
| `tokenizer` | `Callable[[str], int]` | Contador de tokens; default usa `tiktoken` (cl100k_base) se instalado, senão aproximação `len/3.5`. |
| `source` | `str \| None` | Identificador do documento para gravar em cada chunk. |
| `min_tokens` | `int` | Quando > 0, mescla chunks menores com o anterior. |

### Garantias estruturais

- **Não quebra dentro de blocos fenced** ou tabelas — eles permanecem íntegros.
- **Overlap fica restrito à mesma seção** (não cruza headings) para evitar
  contaminação semântica.
- **Breadcrumb completo**: cada chunk traz `heading_path = ["Cap", "Seção", ...]`.
- **Oversized**: se um único bloco excede `max_tokens` e não pode ser dividido,
  o chunk recebe `oversized=True`.

### Exemplo

```python
from markdown_hero import extract_chunks

chunks = extract_chunks(open("doc.md").read(), purpose="rag", source="doc.md")
for c in chunks:
    print(f"[{' › '.join(c.heading_path)}] tokens={c.token_count} type={c.type}")
    print(c.text[:80])
```

### Boas práticas para RAG

- Use `purpose="rag"` (estrutural + sub-split + overlap pequeno).
- Indexe `heading_path` como metadado: filtros por seção dão grandes ganhos.
- Para documentos heterogêneos (código + prosa), o campo `type` permite roteamento
  diferente no embedding/recuperação.

---

<a id="word_format"></a>

## 3. `word_format(md, output_path, *, template=None, style_overrides=None) -> Path`

Renderiza Markdown em `.docx` com um conjunto de estilos profissionais.

### Parâmetros

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `md` | `str \| Path` | Conteúdo ou caminho de arquivo Markdown. |
| `output_path` | `str \| Path` | Destino do `.docx`. |
| `template` | `str \| Path \| None` | Template `.docx` cujos estilos serão usados como base. |
| `style_overrides` | `dict \| None` | Sobrescreve chaves do dicionário `DEFAULT_STYLES`. |

### Conjunto de estilos default (`DEFAULT_STYLES`)

```python
{
    "body_font": "Calibri",
    "code_font": "Consolas",
    "body_size": 11,
    "code_size": 10,
    "heading_sizes": {1: 18, 2: 14, 3: 12, 4: 11, 5: 11, 6: 11},
    "code_bg": "F5F5F5",
    "table_header_bg": "E7E6E6",
    "link_color": "0563C1",
    "table_caption_centered": True,
    "table_repeat_header": True,
}
```

### Mapeamento Markdown → estilo Word

| Elemento | Estilo Word | Detalhes |
|---|---|---|
| `# H1`–`###### H6` | `Heading 1`–`Heading 6` | Tamanhos por nível, **bold**. |
| Parágrafo | `Normal` | Calibri 11pt. |
| **bold**, *italic*, ~~strike~~ | inline runs | aplicado caractere a caractere. |
| `inline code` | run com `Code Char` | Consolas 10pt, fundo `#F5F5F5`. |
| ```` ```bloco``` ```` | `Code Block` (custom) | Consolas 10pt, fundo `#F5F5F5`. |
| `> citação` | `Quote` | Itálico, recuo. |
| `- lista` / `1. lista` | `List Bullet` / `List Number` | Estilos nativos do Word. |
| Tabela | `Table Grid` + cabeçalho `#E7E6E6` | Cabeçalho **bold**, repete em quebras de página. |
| `Table: legenda` | `Caption` | Centralizado, itálico, 10pt, acima da tabela. |
| Link | run com hyperlink | Azul `#0563C1`, sublinhado. |
| `---` | `Horizontal rule` | Borda inferior. |

### Exemplo

```python
from markdown_hero import word_format
word_format("relatorio.md", "relatorio.docx")

# Com template do usuário (preserva cabeçalho/rodapé/marca):
word_format("relatorio.md", "relatorio.docx", template="empresa-base.docx")

# Sobrescrevendo estilos:
word_format(
    "relatorio.md",
    "relatorio.docx",
    style_overrides={"body_size": 12, "code_bg": "EFEFEF"},
)
```

---

<a id="markdown_append"></a>

## 4. `markdown_append(*paths, output, separator="\n\n", frontmatter="merge", headings="shift") -> Path`

Concatena vários arquivos Markdown em um único arquivo de saída.

### Modos de `frontmatter`

| Valor | Comportamento |
|---|---|
| `merge` (default) | Combina todos em um único bloco. Conflitos preservam o primeiro e listam em `_conflicts`. |
| `first` | Mantém só o frontmatter do primeiro arquivo. |
| `drop` | Remove de todos. |
| `all` | Preserva cada bloco sequencialmente (raramente útil). |

### Modos de `headings`

| Valor | Comportamento |
|---|---|
| `shift` (default) | Se o primeiro arquivo tem H1, os demais sofrem shift +1 para evitar dois H1. |
| `preserve` | Não altera headings. |
| `wrap` | Cada arquivo entra como uma seção sob `# {filename ou title do frontmatter}`. |

### Exemplo

```python
from markdown_hero import markdown_append

markdown_append(
    "intro.md", "cap1.md", "cap2.md",
    output="livro.md",
    frontmatter="merge",
    headings="shift",
)
```

---

<a id="markdown_break"></a>

## 5. `markdown_break(path, delimiter, *, include_delimiter="none", output_dir, name_pattern="{stem}_{i:03d}.md", frontmatter="replicate", is_regex=False) -> list[Path]`

Quebra um arquivo Markdown em **N+1** partes nos pontos onde o delimitador
ocorre **N** vezes.

### Parâmetros

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `delimiter` | `str \| re.Pattern \| Iterable` | Aceita string literal, regex compilado ou lista misturando os dois. |
| `is_regex` | `bool` | Quando `True`, interpreta a string como regex (com flag `re.MULTILINE`). |
| `include_delimiter` | `"before"\|"after"\|"none"` | Onde fica o texto do delimitador (final do anterior, início do próximo, ou descartado). |
| `output_dir` | `str \| Path` | Diretório de destino (criado se necessário). |
| `name_pattern` | `str` | Template do nome de cada parte. Recebe `stem` (do arquivo original) e `i` (índice). |
| `frontmatter` | `"replicate"\|"first"\|"drop"` | Tratamento do YAML frontmatter. Em `replicate`, cada parte ganha `part: i` e `part_of: N`. |

### Tratamento de espaços

Cada parte é gerada com `lstrip`/`rstrip` removendo espaços e quebras nas
bordas — exatamente como você especificou: a separação termina no último
caractere visível antes do delimitador e começa no primeiro depois.

### Exemplo

```python
from markdown_hero import markdown_break

# 1) Quebra por separador literal
markdown_break("livro.md", "---SEP---", output_dir="partes/")

# 2) Quebra por regex em headings de nível 1
markdown_break(
    "livro.md", r"^# .+$", is_regex=True,
    include_delimiter="after", output_dir="capitulos/",
    name_pattern="cap_{i:02d}.md",
)

# 3) Múltiplos delimitadores
markdown_break("doc.md", ["===", "---END---"], output_dir="parts/")
```

---

<a id="markdown_merge"></a>

## 6. `markdown_merge(*paths, output, dedupe_headings=True, rebuild_toc=False, separator="\n\n") -> Path`

Append “inteligente”: usa `markdown_append` com merge de frontmatter e shift
de headings, e adicionalmente:

- **Dedupe de headings**: remove seções com heading idêntico **consecutivo**.
- **TOC opcional**: regenera um sumário marcado por `<!-- TOC -->` / `<!-- /TOC -->`.

```python
from markdown_hero import markdown_merge

markdown_merge("a.md", "b.md", output="merged.md", rebuild_toc=True)
```

---

<a id="extracao"></a>

## 7. Funções de extração

| Função | Retorno |
|---|---|
| `extract_frontmatter(md)` | `dict` (vazio se não houver) |
| `remove_frontmatter(md)` | `(corpo, metadados)` |
| `extract_links(md)` | `list[Link]` (inline + autolink) |
| `extract_images(md)` | `list[Image]` |
| `extract_tables(md)` | `list[Table]` (com `headers`, `rows`, `alignments`) |
| `extract_code_blocks(md, language=None)` | `list[CodeBlock]` (filtrável por linguagem) |
| `extract_headings(md)` | `list[Heading]` (com nível, anchor estilo GitHub) |
| `build_toc(md, max_depth=3)` | `str` (Markdown) |

Todos ignoram conteúdo dentro de blocos fenced (matches em `print("[link](x)")`
não são extraídos como link).

```python
from markdown_hero import extract_links, build_toc
for link in extract_links(open("doc.md").read()):
    print(link.line, link.url)

print(build_toc(open("doc.md").read(), max_depth=2))
```

---

<a id="transformacao"></a>

## 8. Funções de transformação

| Função | Descrição |
|---|---|
| `normalize(md, unify_lists=True, trim_trailing=True, collapse_blank_lines=True)` | Padroniza espaços/marcadores. |
| `slugify(text)` | Slug compatível com GitHub/Pandoc. |
| `shift_headings(md, by)` | Rebaixa/eleva headings, ignorando blocos de código; clamp em [1, 6]. |
| `strip_html(md)` | Remove tags HTML inline. |
| `strip_images(md, keep_alt=True)` | Remove imagens (mantendo o alt opcionalmente). |
| `strip_links(md, keep_text=True)` | Remove links (mantendo o texto opcionalmente). |
| `strip_code_blocks(md, keep_inline=False)` | Remove blocos fenced; opcionalmente também inline code. |
| `md_to_plain(md)` | Texto plano preservando parágrafos (mais leve que `strip`). |

---

<a id="lint"></a>

## 9. Lint e métricas

### `lint(md) -> list[Issue]`

Detecta:

| Regra | Severidade | Descrição |
|---|---|---|
| `heading-skip` | warning | H1 → H3 sem H2 intermediário, etc. |
| `duplicate-anchor` | warning | Dois headings geram a mesma âncora. |
| `empty-link-text` | warning | `[](url)` |
| `empty-link-url` | warning | `[texto]()` ou `[texto](#)` |
| `unclosed-fence` | error | Bloco de código sem fechamento. |

```python
from markdown_hero import lint
for issue in lint(open("doc.md").read()):
    print(f"L{issue.line} {issue.severity}: {issue.rule} — {issue.message}")
```

### `word_count(md, ignore_code=True) -> int`

Conta palavras do conteúdo textual, ignorando blocos de código por default.

### `reading_time(md, wpm=200) -> float`

Tempo de leitura em minutos (200 WPM ≈ leitor médio em prosa).

---

<a id="cli"></a>

## 10. CLI — `markdown-hero`

```text
markdown-hero strip   <input> [-o OUT] [--no-numbers] [--keep-math] [--keep-latex-text]
markdown-hero chunk   <input> [-o OUT] [--purpose rag|finetune|summary|generic]
                              [--max-tokens N] [--overlap N]
markdown-hero append  <input...> -o OUT [--separator SEP] [--frontmatter ...] [--headings ...]
markdown-hero break   <input> <delim> --output-dir DIR [--regex] [--include before|after|none]
                              [--frontmatter replicate|first|drop]
markdown-hero merge   <input...> -o OUT [--no-dedupe] [--toc]
markdown-hero word    <input> -o OUT [--template TEMPLATE.docx]
markdown-hero lint    <input> [--json] [-o OUT]
markdown-hero stats   <input>
```

Use `-` como `<input>` para ler de stdin.

```bash
echo "**oi**" | markdown-hero strip -
# oi

markdown-hero chunk doc.md --purpose rag --max-tokens 512 -o chunks.json
markdown-hero word doc.md -o doc.docx --template empresa.docx
markdown-hero break livro.md "## " --regex --include after --output-dir secoes/
```

`lint` retorna **exit code 1** quando há issues `error` (útil em CI).

---

<a id="modelos"></a>

## 11. Modelos de dados

```python
@dataclass
class Link:        text: str; url: str; title: str|None; line: int; type: Literal["inline","reference","autolink"]

@dataclass
class Image:       alt: str; url: str; title: str|None; line: int

@dataclass
class Table:       headers: list[str]; rows: list[list[str]]; alignments: list[str]; line: int

@dataclass
class CodeBlock:   code: str; language: str|None; line: int; fenced: bool

@dataclass
class Heading:     level: int; text: str; line: int; anchor: str

@dataclass
class Chunk:
    text: str
    heading_path: list[str]
    char_start: int; char_end: int
    token_count: int
    type: Literal["prose","code","table","list","mixed"]
    source: str|None
    index: int
    oversized: bool
    metadata: dict
```

---

<a id="design"></a>

## 12. Decisões de design

- **Dialeto-alvo**: GFM. Cobre 95% dos casos reais (GitHub, Obsidian, Notion
  export). MyST/CommonMark não estão totalmente suportados na 0.1.
- **Dependências mínimas**: `markdown-it-py`, `mdit-py-plugins`, `python-docx`,
  `PyYAML`. `tiktoken` é opcional (extra `tokenizers`).
- **Idioma**: `strip` é multilíngue via `unicodedata.NFKD` — não há tabela
  específica para PT.
- **Símbolos matemáticos**: por default são deletados sem deixar espaço, o
  que une tokens (`p=2` → `p2`). Com `keep_math=True` são preservados.
- **Pontuação genérica**: vira espaço, depois espaços são colapsados.
- **Blocos de código** são intocados pelas funções de transformação (`shift_headings`,
  `strip_html`, etc.). Isso evita corromper conteúdo técnico.
- **Frontmatter**: detectado **somente no início** do arquivo, delimitado por
  `---` em linhas próprias.
- **Ordem dos resultados**: `extract_*` retorna na ordem de aparição no documento,
  com `line` 1-based.

---

<a id="limites"></a>

## 13. Limites e considerações de segurança

### Tamanho de arquivo

`markdown_hero` carrega o documento inteiro em memória (`Path.read_text`).
Não há suporte a streaming. Para documentos típicos (até alguns MB) isso
é adequado e mantém a API simples; para arquivos muito grandes
(centenas de MB), recomenda-se quebrar previamente o conteúdo com
ferramentas externas antes de chamar a biblioteca.

### `markdown_break` com `is_regex=True` e input não confiável

Quando `is_regex=True`, o argumento `delimiter` é compilado diretamente
via `re.compile`. **Não passe input não confiável** (vindo de usuários
finais sem validação) como regex: padrões maliciosos podem causar
*ReDoS* (exponential backtracking). Se a entrada vem de um usuário,
mantenha o default `is_regex=False` ou valide o padrão antes.

### Frontmatter e YAML

`extract_frontmatter` usa `yaml.safe_load` (não `yaml.load`), o que
impede deserialização de objetos Python arbitrários. Mesmo assim,
valide o conteúdo antes de usar valores em operações sensíveis (ex.:
montar paths a partir de `metadata["filename"]`).

### Limitação do parser

A biblioteca usa expressões regulares para o reconhecimento estrutural
em vez de um parser CommonMark/GFM completo. Cobre o subconjunto
documentado em `docs/reference.md` mas pode divergir de implementações
de referência em casos extremos (listas profundamente aninhadas,
HTML inline complexo, links de referência em múltiplas linhas).
