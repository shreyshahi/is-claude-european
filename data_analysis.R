rm(list=ls())
library("tidyverse")
# Lets see if there is any difference in accuracy by month

data = read_csv("./correct_counts.csv")

data %>%
  mutate(low = qbinom(0.025, 1000, num_correct / 1000)) %>%
  mutate(high = qbinom(0.975, 1000, num_correct / 1000)) %>%
  ggplot(aes(x = system_date, y = num_correct)) +
  geom_point(size = 2) +
  geom_errorbar(aes(ymin = low, ymax = high), width = 10) +
  theme_minimal() +
  labs(title = "Correct Answers from 1000 Random GSM8K Problems",
       subtitle = "With 95% Confidence Interval",
       x = "Date",
       y = "Number of Correct Answers") +
  scale_x_date(date_breaks = "1 month", date_labels = "%b %Y") +
  ylim(c(850, 1000)) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# lets see if there is any difference in length of answers

data = read_csv("./response_lengths.csv")

normalized_data = data %>%
  group_by(problem_number) %>%
  mutate(normalized_chars = scale(num_characters)) %>%
  ungroup() %>%
  group_by(system_date) %>%
  summarize(
    mean_norm = mean(normalized_chars),
    median_norm = median(normalized_chars),
    sd_norm = sd(normalized_chars)
  )

normalized_data
