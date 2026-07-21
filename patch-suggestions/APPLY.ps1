<#
.SYNOPSIS
  Applique le patch "Suggestions de recettes" sur un clone local du repo supmeal.

.DESCRIPTION
  Copie les 14 fichiers modifies/ajoutes depuis ce dossier vers le repertoire
  de travail courant (le repo supmeal). Concu pour etre execute depuis la racine
  du clone (la ou se trouvent docker-compose.yml, README.md, backend/, etc.).

  A executer avec :
    .\APPLY.ps1

  Les conflits (fichiers locaux differents) sont signales mais ne sont pas
  ecrases silencieusement.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $scriptDir)

$items = @(
    @{ src = "patch-suggestions\README.md";                                   dst = "README.md" },
    @{ src = "patch-suggestions\backend\app\schemas\recipe.py";               dst = "backend\app\schemas\recipe.py" },
    @{ src = "patch-suggestions\backend\app\api\v1\endpoints\recipes.py";    dst = "backend\app\api\v1\endpoints\recipes.py" },
    @{ src = "patch-suggestions\backend\tests\test_suggest.py";              dst = "backend\tests\test_suggest.py" },
    @{ src = "patch-suggestions\frontend\src\lib\types.ts";                   dst = "frontend\src\lib\types.ts" },
    @{ src = "patch-suggestions\frontend\src\pages\SuggestionsPage.tsx";      dst = "frontend\src\pages\SuggestionsPage.tsx" },
    @{ src = "patch-suggestions\frontend\src\App.tsx";                        dst = "frontend\src\App.tsx" },
    @{ src = "patch-suggestions\frontend\src\components\Layout.tsx";          dst = "frontend\src\components\Layout.tsx" },
    @{ src = "patch-suggestions\docs\user\README.md";                         dst = "docs\user\README.md" },
    @{ src = "patch-suggestions\docs\user\06-suggestions.md";                 dst = "docs\user\06-suggestions.md" },
    @{ src = "patch-suggestions\docs\technical\03-api.md";                    dst = "docs\technical\03-api.md" },
    @{ src = "patch-suggestions\docs\technical\08-checklist-rendu.md";        dst = "docs\technical\08-checklist-rendu.md" },
    @{ src = "patch-suggestions\docs\screenshots\README.md";                  dst = "docs\screenshots\README.md" },
    @{ src = "patch-suggestions\docs\screenshots\.gitkeep";                   dst = "docs\screenshots\.gitkeep" }
)

$ok = 0; $skipped = 0
foreach ($it in $items) {
    $src = Join-Path $scriptDir $it.src
    $dst = Join-Path (Get-Location) $it.dst
    if (-not (Test-Path $src)) {
        Write-Warning "MISSING: $src"
        continue
    }
    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    Write-Host "  OK   $($it.dst)"
    $ok++
}

Write-Host ""
Write-Host "$ok fichiers appliques depuis $($items.Count)."
Write-Host ""
Write-Host "Prochaines etapes :"
Write-Host "  1. cd <votre-clone-supmeal>"
Write-Host "  2. git add -A"
Write-Host "  3. git commit -m `"feat(recipes): smart suggestions by ingredients + docs`""
Write-Host "  4. git push origin main"
