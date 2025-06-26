DESCRIPTION = """
## About this App
This app demonstrates a semi-supervised method to tune and optimize an LLM prompt inspired by neural network training loops, leveraging LLM-as-a-Judge for to calculate "loss", and LLM-as-a-Judge as our "optimizer" *and* early stopper.

While this application demonstrates a proof-of-concept, it is intended to be adapted for specific use cases. This toy example tunes a prompt for analysis on a single dataset, but it could be modified to tune a prompt across multiple sets of inputs and outputs, observing the evaluations at scale, and iteratively improving the input prompt. To manage this complexity, consider modifying the `Optimizer Prompt` to two steps. You could use one LLM to aggregate the errors at scale and attribute labels to them, much like error analysis, and then use an additional LLM to observe the error analysis and suggest improvements to the input prompt. This framework is even extensible to early stopping criteria and evaluation on holdout sets.

Because we understand LLMs can and will hallucinate, and because they are trained to "complete" their thoughts rather than truly predict, you may be tempted to dismiss the affectiveness of this tuning method... but consider the practically of this at scale! We can't, and shouldn't, eliminate human-in-the-loop, but even a few turns through this process can likely yield a more effective prompt than what you initially started with.


### Starting Prompt
Our initial prompt follows basic prompt engineering techniques, such as giving the LLM an identity, a task, some context data, and instructions.


### Evaluation ("Loss") Prompts
The evaluation prompts are designed to evaluate the output of our starting prompt across different verticals, and follow a more formal structure of an identity, context, task, scoring rubric with output examples, output format, and lastly the related data to evaluate (input prompt, input data, & LLM output from the input prompt).

While these are generic evaluation prompts to be adapted to any use, and can be extended on for specific domains (Marketing, Finance, etc).


### Optimizer Prompt
The optimizer prompt is the most formal and rigid, as is necessary for understanding the input context, evaluation context, and improving upon the input prompt. 
"""

DUMMY_DATA = """
Quarter,Revenue ($M),Profit Margin (%),Customer Satisfaction (%),Enterprise Growth (%),Consumer Growth (%),Marketing Spend ($M),R&D Investment ($M),Employee Count,Churn Rate (%),New Product Revenue ($M),Regional Performance
Q1 2024,4.1,12.5,85,38,-8,0.8,0.3,145,5.2,0.4,"NA: 2.1M, EU: 1.3M, APAC: 0.7M"
Q2 2024,4.3,13.1,87,41,-5,0.9,0.35,152,4.8,0.6,"NA: 2.2M, EU: 1.4M, APAC: 0.7M"
Q3 2024,5.18,15.3,72,45,-12,1.2,0.42,148,7.9,1.1,"NA: 2.8M, EU: 1.6M, APAC: 0.78M"
Q4 2024,5.95,14.8,78,52,-15,1.1,0.38,155,6.4,1.3,"NA: 3.1M, EU: 1.7M, APAC: 1.15M"
Q1 2025,6.2,16.2,81,48,-18,0.95,0.45,162,5.9,1.4,"NA: 3.2M, EU: 1.8M, APAC: 1.2M"
Q2 2025,5.8,15.9,83,44,-22,1.05,0.41,158,6.1,1.2,"NA: 2.9M, EU: 1.7M, APAC: 1.2M"
Q3 2025,7.1,17.4,79,51,-25,1.3,0.48,165,7.2,1.8,"NA: 3.6M, EU: 2.0M, APAC: 1.5M"
Q4 2025,6.85,16.8,82,49,-28,1.25,0.52,171,6.8,1.65,"NA: 3.4M, EU: 1.95M, APAC: 1.5M"
"""

dataset_details = """
Data Complexity Challenges:

Counterintuitive Relationships: Customer satisfaction drops in Q3 2024 despite highest profit margins, creating analytical puzzles
Contradictory Trends: Revenue generally increases while consumer growth consistently declines (goes more negative), which could confuse correlation analysis
Non-linear Patterns: Q2 2025 shows revenue decline despite continued investment, breaking simple trend assumptions
Multi-dimensional Regional Data: Complex regional performance strings that require parsing and could be misinterpreted
Seasonal vs. Structural Changes: Employee count fluctuates (decreases in Q3 2024, Q2 2025) which could be mistaken for downsizing when it might be seasonal
Compound Metrics: Churn rate peaks don't always align with satisfaction lows, creating analytical complexity
Investment ROI Ambiguity: R&D and marketing spend don't show clear correlation with new product revenue or growth

Potential LLM Errors:

Misinterpreting negative consumer growth as positive (focusing on the number getting "bigger")
Assuming all metrics should correlate positively
Misreading the regional data format
Drawing causal conclusions from correlation
Missing the cyclical nature of some metrics
Incorrectly parsing the complex regional performance data
"""