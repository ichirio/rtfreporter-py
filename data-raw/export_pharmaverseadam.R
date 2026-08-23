suppressMessages(library(dplyr))

out <- "C:/Users/ichir/AppData/Local/Temp/claude/C--Users-ichir/298bf4c8-6f5b-4394-8cf8-1ebb4778911c/scratchpad/adam_ship"
dir.create(out, showWarnings = FALSE, recursive = TRUE)

arm_levels <- c("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")

adsl_raw <- pharmaverseadam::adsl
adae_raw <- pharmaverseadam::adae

cat("adae has AESOC:", "AESOC" %in% names(adae_raw), "\n")

adsl <- adsl_raw |>
  filter(TRT01A %in% arm_levels) |>
  select(USUBJID, TRT01A, AGE, SEX, RACE, ETHNIC, SAFFL)

adae <- adae_raw |>
  filter(TRT01A %in% arm_levels, TRTEMFL == "Y") |>
  select(USUBJID, TRT01A, AESOC, AEDECOD, TRTEMFL)

write.csv(adsl, file.path(out, "adsl.csv"), row.names = FALSE, na = "")
write.csv(adae, file.path(out, "adae.csv"), row.names = FALSE, na = "")

cat("adsl rows:", nrow(adsl), " adae rows:", nrow(adae), "\n")

arm_n <- table(factor(adsl$TRT01A, levels = arm_levels))
cat("\n=== ARM N (denominators) ===\n")
print(arm_n)

# ---- Reference numbers for the DM table (so Python can be validated) ----
d <- adsl |>
  mutate(TRT01A = factor(TRT01A, levels = arm_levels),
         AGEGR = cut(AGE, breaks = c(-Inf, 65, 81, Inf),
                     labels = c("<65", "65 - 80", ">80"), right = FALSE))

cat("\n=== AGE summary by arm ===\n")
age_tab <- d |> group_by(TRT01A) |>
  summarise(n = sum(!is.na(AGE)),
            mean = round(mean(AGE), 1), sd = round(sd(AGE), 2),
            median = round(median(AGE), 1),
            min = min(AGE), max = max(AGE), .groups = "drop")
print(as.data.frame(age_tab))

cat("\n=== AGEGR counts by arm ===\n")
print(as.data.frame(d |> count(TRT01A, AGEGR) |> tidyr::pivot_wider(
  names_from = TRT01A, values_from = n, values_fill = 0)))

cat("\n=== SEX counts by arm ===\n")
print(as.data.frame(d |> count(TRT01A, SEX) |> tidyr::pivot_wider(
  names_from = TRT01A, values_from = n, values_fill = 0)))

cat("\n=== RACE counts by arm ===\n")
print(as.data.frame(d |> count(TRT01A, RACE) |> tidyr::pivot_wider(
  names_from = TRT01A, values_from = n, values_fill = 0)))

# ---- Reference numbers for the AE table ----
a <- adae |> mutate(TRT01A = factor(TRT01A, levels = arm_levels))

cat("\n=== ANY AE: distinct subjects with any TEAE, by arm ===\n")
print(a |> distinct(USUBJID, TRT01A) |> count(TRT01A) |> as.data.frame())

cat("\n=== SOC-level distinct subject counts by arm (top 8 SOCs alphabetical) ===\n")
soc <- a |> distinct(USUBJID, TRT01A, AESOC) |> count(TRT01A, AESOC) |>
  tidyr::pivot_wider(names_from = TRT01A, values_from = n, values_fill = 0) |>
  arrange(AESOC)
print(as.data.frame(head(soc, 8)))

cat("\n=== PT order (subject count desc, ties A-Z) - first 15 ===\n")
pt_order <- a |> distinct(USUBJID, AEDECOD) |> count(AEDECOD, name = "tot") |>
  arrange(desc(tot), AEDECOD)
print(as.data.frame(head(pt_order, 15)))

cat("\n=== PTs kept (>= 3% in any arm) ===\n")
keep <- a |> distinct(USUBJID, TRT01A, AEDECOD) |> count(TRT01A, AEDECOD, name = "n") |>
  mutate(p = 100 * n / as.integer(arm_n[as.character(TRT01A)])) |>
  group_by(AEDECOD) |> summarise(mx = max(p), .groups = "drop") |>
  filter(mx >= 3) |> arrange(AEDECOD)
cat("count kept:", nrow(keep), "\n")
print(as.data.frame(keep))
