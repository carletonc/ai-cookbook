DESCRIPTION = """
This app is a template that demonstrates a semi-supervised way to automate prompt tuning inspired by neural network training.

Our initial prompt follows basic prompt engineering techniques, such as giving the LLM an identity, a task, some context data, and instructions.

The evaluation prompts are designed to evaluate the LLMs output across different verticals, and follow a more formal structure of
an identity, context, task, scoring rubric with output examples, output format, along with the related data to evaluate (input prompt, data, & LLM output).

These are general evaluation prompts to be adapted to any use, and can be extended on for specific domains (Marketing, Finance, etc.).

Our tuning prompt is the most formal and rigid, as is necessary for evaluating and improving upon the input prompt.
"""

DUMMY_DATA = """
Quarter,Revenue ($M),Profit Margin (%),Customer Satisfaction (%),Enterprise Growth (%),Consumer Growth (%)
Q1 2024,4.1,12.5,85,38,-8
Q2 2024,4.3,13.1,87,41,-5
Q3 2024,5.18,15.3,72,45,-12
"""