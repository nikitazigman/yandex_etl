for index in movies 
    do  
        elasticdump \
            --input=/backup/es_"$index"_analyzer.json \
            --output=http://127.0.0.1:9200/movies \
            --type=analyzer
        elasticdump \
            --input=/backup/es_"$index"_settings.json \
            --output=http://127.0.0.1:9200/movies \
            --type=settings
        elasticdump \
            --input=/backup/es_"$index"_mapping.json \
            --output=http://127.0.0.1:9200/movies \
            --type=mapping
        elasticdump \
            --input=/backup/es_"$index"_data.json \
            --output=http://127.0.0.1:9200/"$index" \
            --type=data
        
    done