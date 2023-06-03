for index in movies genres persons
    do
        elasticdump \
            --output=/backup/es_"$index"_analyzer.json \
            --input=http://127.0.0.1:9200/movies \
            --type=analyzer

        elasticdump \
            --output=/backup/es_"$index"_settings.json \
            --input=http://127.0.0.1:9200/movies \
            --type=settings
        elasticdump \
            --output=/backup/es_"$index"_mapping.json \
            --input=http://127.0.0.1:9200/movies \
            --type=mapping
        elasticdump \
            --output=/backup/es_"$index"_data.json \
            --input=http://127.0.0.1:9200/"$index" \
            --type=data
    done