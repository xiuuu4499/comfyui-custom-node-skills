# Node Expansion (Subgraph Injection)

Nodes can return a dynamically constructed subgraph that replaces themselves during execution.

## Example: Repeating Subgraph
```python
from comfy_api.latest import io
from comfy_execution.graph_utils import GraphBuilder

class RepeatNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="RepeatNode",
            display_name="Repeat KSampler",
            category="sampling",
            enable_expand=True,          # Required for expansion
            inputs=[
                io.Model.Input("model"),
                io.Int.Input("repeat_count", default=2, min=1, max=10),
                io.Latent.Input("latent"),
            ],
            outputs=[io.Latent.Output("LATENT")],
        )

    @classmethod
    def execute(cls, model, repeat_count, latent):
        graph = GraphBuilder()
        current_latent = latent
        for i in range(repeat_count):
            # Create a subnode in the execution graph
            sampler = graph.node("KSampler",
                model=model,
                latent_image=current_latent,
                # ... other parameters
            )
            current_latent = sampler.out(0)
            
        # Return final output reference and the finalized subgraph
        return io.NodeOutput(current_latent, expand=graph.finalize())
```

---

## Key Rules for Node Expansion
- Set `enable_expand=True` in your `io.Schema`.
- Use `GraphBuilder` from `comfy_execution.graph_utils` to construct subgraphs programmatically and safely.
- Return `io.NodeOutput(output_ref, expand=graph.finalize())` where `output_ref` is the output reference of the last node in the subgraph.
- Subnode IDs in the subgraph must be deterministic and unique to ensure cache validation.
- Each subnode in the expanded subgraph is cached separately.
