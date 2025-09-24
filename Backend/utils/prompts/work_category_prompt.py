def get_work_category(keywords: list)->str:
    return """
        You are an expert in mapping company capabilities and needs in the AI/ML and healthcare software domain.

        You are given a list of keywords describing a company’s focus areas, technology, and market. 

        Your task:
        1. Decide whether this company is more likely to want **lower-level tasks** (such as labeling, curation, or verification of data) or **higher-level tasks** (such as model validation, compliance workflows, audit readiness, regulatory documentation).
        2. Identify *which specific task or tasks* the company would be most interested in from the following categories:
           - Lower-level tasks: labeling, curation, verification
           - Higher-level tasks: model validation, compliance monitoring, regulatory audit support, documentation automation, risk management, lifecycle governance, workflow integration
        3. For each applicable task, assign a **confidence score between 0.0 and 1.0** representing how strongly the company’s keywords align with that task.
        4. Output your answer in structured JSON with the following format:

        {{
          "task_level": "higher or lower",
          "specific_tasks": {{
              "task_name": confidence_score,
          }}
        }}

        Input keywords:
        {keywords}
    """