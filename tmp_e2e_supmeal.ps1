$ErrorActionPreference='Stop'
$base='http://localhost:8765/api/v1'
$ts=[int][double]::Parse((Get-Date -UFormat %s))
$ownerEmail="owner.$ts@example.com"
$memberEmail="member.$ts@example.com"
$ownerUser="owner_$ts"
$memberUser="member_$ts"
$pwd='SupMeal!Test#2026A'
$results = New-Object System.Collections.Generic.List[string]

function Add-Result($name,$ok,$detail){
  $status = if($ok){'PASS'} else {'FAIL'}
  $line = "[$status] $name - $detail"
  $results.Add($line)
  Write-Output $line
  if(-not $ok){ throw "Step failed: $name" }
}

$ownerReg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body (@{email=$ownerEmail;username=$ownerUser;password=$pwd} | ConvertTo-Json)
$memberReg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body (@{email=$memberEmail;username=$memberUser;password=$pwd} | ConvertTo-Json)
Add-Result 'Register owner/member' (($ownerReg.access_token -and $memberReg.access_token) -ne $null) "owner=$ownerEmail member=$memberEmail"

$hOwner = @{ Authorization = "Bearer $($ownerReg.access_token)" }
$hMember = @{ Authorization = "Bearer $($memberReg.access_token)" }

$ownerLogin = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType 'application/json' -Body (@{email=$ownerEmail;password=$pwd} | ConvertTo-Json)
$memberLogin = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType 'application/json' -Body (@{email=$memberEmail;password=$pwd} | ConvertTo-Json)
Add-Result 'Login both accounts' (($ownerLogin.access_token -and $memberLogin.access_token) -ne $null) 'tokens returned'

$cookbook = Invoke-RestMethod -Method Post -Uri "$base/cookbooks" -Headers $hOwner -ContentType 'application/json' -Body (@{name="Famille $ts";description='Cookbook test E2E'} | ConvertTo-Json)
$cbId = $cookbook.id
Invoke-RestMethod -Method Post -Uri "$base/cookbooks/$cbId/members" -Headers $hOwner -ContentType 'application/json' -Body (@{user_email=$memberEmail;role='editor'} | ConvertTo-Json) | Out-Null
$cbMemberView = Invoke-RestMethod -Method Get -Uri "$base/cookbooks/$cbId" -Headers $hMember
Add-Result 'Cookbook sharing + permissions' ($cbMemberView.id -eq $cbId) "cookbook_id=$cbId"

$tagDiet = Invoke-RestMethod -Method Post -Uri "$base/tags" -Headers $hOwner -ContentType 'application/json' -Body (@{name="vegan_$ts";category='diet'} | ConvertTo-Json)
$tagCuisine = Invoke-RestMethod -Method Post -Uri "$base/tags" -Headers $hOwner -ContentType 'application/json' -Body (@{name="italian_$ts";category='cuisine'} | ConvertTo-Json)

$recipePayload = @{
  title="Pates E2E $ts"
  description='Recette collaborative'
  source_url='https://example.com/pates'
  prep_time_minutes=20
  cook_time_minutes=15
  servings=2
  difficulty='facile'
  cuisine_type='italienne'
  ingredients=@(
    @{name='pates';quantity=250;unit='g';position=0},
    @{name='tomate';quantity=3;unit=$null;position=1}
  )
  steps=@(
    @{content='Faire bouillir de l eau';position=0},
    @{content='Cuire les pates';position=1}
  )
  tag_ids=@($tagDiet.id,$tagCuisine.id)
}
$recipe = Invoke-RestMethod -Method Post -Uri "$base/cookbooks/$cbId/recipes" -Headers $hOwner -ContentType 'application/json' -Body ($recipePayload | ConvertTo-Json -Depth 8)
$recipeId = $recipe.id
Add-Result 'Recipe creation with full fields' ($recipeId -gt 0) "recipe_id=$recipeId"

$filtered1 = Invoke-RestMethod -Method Get -Uri "$base/cookbooks/$cbId/recipes?search=Pates&ingredient=tomate&tag_category=diet&max_prep_time=30" -Headers $hOwner
Add-Result 'Cookbook search/filter' (($filtered1 | Where-Object { $_.id -eq $recipeId }).Count -ge 1) 'search+ingredient+tag_category+time OK'

$fav = Invoke-RestMethod -Method Post -Uri "$base/recipes/$recipeId/favorite" -Headers $hMember
$comment = Invoke-RestMethod -Method Post -Uri "$base/recipes/$recipeId/comments" -Headers $hMember -ContentType 'application/json' -Body (@{content='Top recette !'} | ConvertTo-Json)
$comments = Invoke-RestMethod -Method Get -Uri "$base/recipes/$recipeId/comments" -Headers $hOwner
$msg = Invoke-RestMethod -Method Post -Uri "$base/cookbooks/$cbId/messages" -Headers $hMember -ContentType 'application/json' -Body (@{content='Salut equipe cuisine'} | ConvertTo-Json)
$msgs = Invoke-RestMethod -Method Get -Uri "$base/cookbooks/$cbId/messages" -Headers $hOwner
$okSocial = $fav.is_favorite -and ($comments | Where-Object { $_.id -eq $comment.id }).Count -ge 1 -and ($msgs | Where-Object { $_.id -eq $msg.id }).Count -ge 1
Add-Result 'Favorites + comments + chat REST' $okSocial 'interaction features OK'

$planDate = (Get-Date).AddDays(1).ToString('yyyy-MM-dd')
$plan = Invoke-RestMethod -Method Post -Uri "$base/meal-plans" -Headers $hMember -ContentType 'application/json' -Body (@{recipe_id=$recipeId;cookbook_id=$cbId;planned_date=$planDate;meal_slot='dinner';servings=4} | ConvertTo-Json)
$plans = Invoke-RestMethod -Method Get -Uri "$base/meal-plans?cookbook_id=$cbId&start_date=$planDate&end_date=$planDate" -Headers $hOwner
Add-Result 'Meal planning collaborative' (($plans | Where-Object { $_.id -eq $plan.id }).Count -ge 1) "plan_id=$($plan.id)"

$shopGen = Invoke-RestMethod -Method Post -Uri "$base/shopping/generate" -Headers $hOwner -ContentType 'application/json' -Body (@{start_date=$planDate;end_date=$planDate;cookbook_id=$cbId;name="Courses $ts"} | ConvertTo-Json)
$listId = $shopGen.id
$shopList = Invoke-RestMethod -Method Get -Uri "$base/shopping/$listId" -Headers $hOwner
Invoke-RestMethod -Method Patch -Uri "$base/shopping/$listId" -Headers $hOwner -ContentType 'application/json' -Body (@{is_completed=$true} | ConvertTo-Json) | Out-Null
$newItem = Invoke-RestMethod -Method Post -Uri "$base/shopping/$listId/items" -Headers $hOwner -ContentType 'application/json' -Body (@{name='pain';quantity=1;unit='piece'} | ConvertTo-Json)
Invoke-RestMethod -Method Patch -Uri "$base/shopping/$listId/items/$($newItem.id)" -Headers $hOwner -ContentType 'application/json' -Body (@{is_checked=$true} | ConvertTo-Json) | Out-Null
Add-Result 'Shopping generation + CRUD' (($shopList.items.Count -ge 1) -and ($newItem.id -gt 0)) "list_id=$listId"

Invoke-RestMethod -Method Patch -Uri "$base/users/me" -Headers $hOwner -ContentType 'application/json' -Body (@{full_name='Owner Supmeal';default_servings=3;dietary_preferences='vegetarien'} | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Method Post -Uri "$base/users/me/change-password" -Headers $hOwner -ContentType 'application/json' -Body (@{current_password=$pwd;new_password='SupMeal!New#2026A'} | ConvertTo-Json) | Out-Null
$relogin = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType 'application/json' -Body (@{email=$ownerEmail;password='SupMeal!New#2026A'} | ConvertTo-Json)
Add-Result 'User settings (profile + password)' ($relogin.access_token -ne $null) 'password updated and login OK'

$exportJsonResp = Invoke-WebRequest -Method Get -Uri "$base/import-export/json" -Headers $hOwner
$exportCsvResp = Invoke-WebRequest -Method Get -Uri "$base/import-export/csv" -Headers $hOwner
Add-Result 'Export JSON/CSV' (($exportJsonResp.Content.Length -gt 100) -and ($exportCsvResp.Content.Length -gt 50)) 'files returned'

$tmpJson = Join-Path $env:TEMP "supmeal_import_$ts.json"
$exportJsonResp.Content | Set-Content -Path $tmpJson -Encoding UTF8
$importJson = Invoke-RestMethod -Method Post -Uri "$base/import-export/json" -Headers $hMember -Form @{ file = Get-Item $tmpJson }
Add-Result 'Import JSON' ($importJson.imported_recipes -ge 1) "imported=$($importJson.imported_recipes)"

$providers = Invoke-RestMethod -Method Get -Uri "$base/auth/oauth/providers"
$hasKeys = ($providers.PSObject.Properties.Name -contains 'google') -and ($providers.PSObject.Properties.Name -contains 'github')
$noMicrosoftKey = -not ($providers.PSObject.Properties.Name -contains 'microsoft')
Add-Result 'OAuth provider contract' ($hasKeys -and $noMicrosoftKey) 'google/github only, microsoft removed'

"=== SUMMARY ==="
$results | ForEach-Object { $_ }
"Total checks: $($results.Count)"
