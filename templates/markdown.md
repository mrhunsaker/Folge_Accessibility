# {{title}}

{% if description %}
> {{description}}

{% endif %}

{% for step in steps %}
## Step {{step.step_id}}: {{step.title}}

{{step.body}}

{% if step.image %}
![{{step.vision.alt_text}}]({{step.image}}){longdesc="{{step.vision.long_description | replace('"', '\\"')}}"}

{% if include_long_descriptions %}
<div class="image-description">
**Image Description:** {{step.vision.long_description}}
</div>

{% endif %}
{% endif %}

{% if not loop.last and newpage_enabled %}
\newpage

{% endif %}
{% endfor %}
