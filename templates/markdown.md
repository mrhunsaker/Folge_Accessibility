# {{title}}

{% if description %}
> {{description}}

{% endif %}

{% for step in steps %}
## Step {{loop.index}}: {{step.title}}

{{step.body}}

{% if step.image %}
{% if step.vision %}
![{{step.vision.alt_text}}]({{image_prefix}}{{step.image}}){longdesc="{{step.vision.long_description | replace('"', '\\"')}}"}

{% if include_long_descriptions %}
<div class="image-description">
**Image Description:** {{step.vision.long_description}}
</div>

{% endif %}
{% else %}
![Image needs manual alt text]({{image_prefix}}{{step.image}}){longdesc="Manual description required"}

{% if include_long_descriptions %}
<div class="image-description">
**Image Description:** *Vision processing failed for this step. Please provide a manual description.*
</div>

{% endif %}
{% endif %}
{% endif %}

{% if not loop.last and newpage_enabled %}
\newpage

{% endif %}
{% endfor %}
