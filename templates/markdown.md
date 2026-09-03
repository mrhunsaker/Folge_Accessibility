# {{title}}

{% if description %}
> {{description}}

{% endif %}

{% set ns = namespace(step_number=1) %}
{% for step in steps %}
{% if step.step_label is defined and step.step_label is not none %}
{% set label_num = step.step_label | replace('Step', '') | replace(' ', '') | int(default=0) %}
{% if label_num > 0 %}
{% set ns.step_number = label_num + 1 %}
{% endif %}
##{{ ' ' if step.step_label }}{{step.step_label}} {{step.title}}
{% else %}
## Step {{ns.step_number}}: {{step.title}}
{% set ns.step_number = ns.step_number + 1 %}
{% endif %}

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
